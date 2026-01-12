"""
CRM API Endpoints

Manages prospects, activities, and callbacks for TSG Safety consulting CRM.
Prospects are linked to OSHA Inspection records.
"""
from datetime import date, datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, desc, and_, or_
from pydantic import BaseModel

from src.database.connection import get_db
from src.database.models import (
    Inspection, Company, Prospect, Activity, Callback,
    ProspectStatus, ActivityType, CallbackStatus
)

router = APIRouter()


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class ActivityResponse(BaseModel):
    """Response model for activity."""
    id: int
    prospect_id: int
    activity_type: str
    subject: Optional[str]
    description: Optional[str]
    outcome: Optional[str]
    activity_date: datetime
    duration_minutes: Optional[int]
    task_due_date: Optional[date]
    task_completed: Optional[bool]
    task_completed_date: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class CallbackResponse(BaseModel):
    """Response model for callback."""
    id: int
    prospect_id: int
    callback_date: datetime
    callback_type: Optional[str]
    notes: Optional[str]
    status: str
    completed_at: Optional[datetime]
    created_at: datetime
    # Include prospect info for dashboard widget
    estab_name: Optional[str] = None
    site_state: Optional[str] = None

    class Config:
        from_attributes = True


class ProspectResponse(BaseModel):
    """Response model for prospect."""
    id: int
    inspection_id: int
    status: str
    priority: Optional[str]
    estimated_value: Optional[float]
    notes: Optional[str]
    next_action: Optional[str]
    next_action_date: Optional[date]
    lost_reason: Optional[str]
    won_date: Optional[date]
    won_value: Optional[float]
    created_at: datetime
    updated_at: datetime
    # Inspection/Company info
    activity_nr: Optional[str] = None
    estab_name: Optional[str] = None
    site_address: Optional[str] = None
    site_city: Optional[str] = None
    site_state: Optional[str] = None
    site_zip: Optional[str] = None
    total_current_penalty: Optional[float] = None
    open_date: Optional[date] = None
    # Counts
    activity_count: int = 0
    callback_count: int = 0

    class Config:
        from_attributes = True


class ProspectDetailResponse(ProspectResponse):
    """Response model for prospect with activities and callbacks."""
    activities: List[ActivityResponse] = []
    callbacks: List[CallbackResponse] = []

    class Config:
        from_attributes = True


class ProspectListResponse(BaseModel):
    """Paginated list response for prospects."""
    items: List[ProspectResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CreateProspectRequest(BaseModel):
    """Request model for creating a prospect."""
    inspection_id: int
    status: Optional[str] = "new_lead"
    priority: Optional[str] = None
    estimated_value: Optional[float] = None
    notes: Optional[str] = None
    next_action: Optional[str] = None
    next_action_date: Optional[date] = None


class UpdateProspectRequest(BaseModel):
    """Request model for updating a prospect."""
    status: Optional[str] = None
    priority: Optional[str] = None
    estimated_value: Optional[float] = None
    notes: Optional[str] = None
    next_action: Optional[str] = None
    next_action_date: Optional[date] = None
    lost_reason: Optional[str] = None
    won_date: Optional[date] = None
    won_value: Optional[float] = None


class CreateActivityRequest(BaseModel):
    """Request model for creating an activity."""
    activity_type: str
    subject: Optional[str] = None
    description: Optional[str] = None
    outcome: Optional[str] = None
    activity_date: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    task_due_date: Optional[date] = None


class UpdateActivityRequest(BaseModel):
    """Request model for updating an activity."""
    subject: Optional[str] = None
    description: Optional[str] = None
    outcome: Optional[str] = None
    task_completed: Optional[bool] = None


class CreateCallbackRequest(BaseModel):
    """Request model for creating a callback."""
    callback_date: datetime
    callback_type: Optional[str] = None
    notes: Optional[str] = None


class UpdateCallbackRequest(BaseModel):
    """Request model for updating a callback."""
    callback_date: Optional[datetime] = None
    callback_type: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class CRMStatsResponse(BaseModel):
    """Response model for CRM dashboard stats."""
    total_prospects: int
    by_status: dict
    upcoming_callbacks: int
    overdue_callbacks: int
    tasks_due_today: int
    total_pipeline_value: float
    won_this_month: int
    won_value_this_month: float


# =============================================================================
# PROSPECT ENDPOINTS
# =============================================================================

@router.get("/prospects", response_model=ProspectListResponse)
async def list_prospects(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    search: Optional[str] = Query(None, description="Search company name"),
    state: Optional[str] = Query(None, description="Filter by state"),
    has_upcoming_callback: Optional[bool] = Query(None, description="Filter by upcoming callbacks"),
    sort_by: str = Query("updated_at", description="Sort field"),
    sort_desc: bool = Query(True, description="Sort descending"),
    db: Session = Depends(get_db),
):
    """List prospects with filtering and pagination."""
    # Base query
    query = select(Prospect).options(joinedload(Prospect.inspection))

    # Apply filters
    if status:
        query = query.where(Prospect.status == status)
    if priority:
        query = query.where(Prospect.priority == priority)
    if state:
        query = query.join(Inspection).where(Inspection.site_state == state)
    if search:
        query = query.join(Inspection).where(
            Inspection.estab_name.ilike(f"%{search}%")
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar()

    # Apply sorting
    sort_column = getattr(Prospect, sort_by, Prospect.updated_at)
    if sort_desc:
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(sort_column)

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    prospects = db.execute(query).scalars().unique().all()

    # Build response items with inspection data
    items = []
    for prospect in prospects:
        insp = prospect.inspection

        # Count activities and callbacks
        activity_count = db.execute(
            select(func.count(Activity.id)).where(Activity.prospect_id == prospect.id)
        ).scalar()
        callback_count = db.execute(
            select(func.count(Callback.id)).where(
                and_(Callback.prospect_id == prospect.id, Callback.status == CallbackStatus.PENDING)
            )
        ).scalar()

        items.append(ProspectResponse(
            id=prospect.id,
            inspection_id=prospect.inspection_id,
            status=prospect.status.value if prospect.status else "new_lead",
            priority=prospect.priority,
            estimated_value=prospect.estimated_value,
            notes=prospect.notes,
            next_action=prospect.next_action,
            next_action_date=prospect.next_action_date,
            lost_reason=prospect.lost_reason,
            won_date=prospect.won_date,
            won_value=prospect.won_value,
            created_at=prospect.created_at,
            updated_at=prospect.updated_at,
            activity_nr=insp.activity_nr if insp else None,
            estab_name=insp.estab_name if insp else None,
            site_address=insp.site_address if insp else None,
            site_city=insp.site_city if insp else None,
            site_state=insp.site_state if insp else None,
            site_zip=insp.site_zip if insp else None,
            total_current_penalty=insp.total_current_penalty if insp else None,
            open_date=insp.open_date if insp else None,
            activity_count=activity_count,
            callback_count=callback_count,
        ))

    total_pages = (total + page_size - 1) // page_size

    return ProspectListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/prospects/{prospect_id}", response_model=ProspectDetailResponse)
async def get_prospect(
    prospect_id: int,
    db: Session = Depends(get_db),
):
    """Get prospect detail with activities and callbacks."""
    prospect = db.execute(
        select(Prospect)
        .options(
            joinedload(Prospect.inspection),
            joinedload(Prospect.activities),
            joinedload(Prospect.callbacks),
        )
        .where(Prospect.id == prospect_id)
    ).scalar()

    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    insp = prospect.inspection

    # Build activity responses
    activities = [
        ActivityResponse(
            id=a.id,
            prospect_id=a.prospect_id,
            activity_type=a.activity_type.value if a.activity_type else None,
            subject=a.subject,
            description=a.description,
            outcome=a.outcome,
            activity_date=a.activity_date,
            duration_minutes=a.duration_minutes,
            task_due_date=a.task_due_date,
            task_completed=a.task_completed,
            task_completed_date=a.task_completed_date,
            created_at=a.created_at,
        )
        for a in sorted(prospect.activities, key=lambda x: x.activity_date or datetime.min, reverse=True)
    ]

    # Build callback responses
    callbacks = [
        CallbackResponse(
            id=c.id,
            prospect_id=c.prospect_id,
            callback_date=c.callback_date,
            callback_type=c.callback_type,
            notes=c.notes,
            status=c.status.value if c.status else "pending",
            completed_at=c.completed_at,
            created_at=c.created_at,
        )
        for c in sorted(prospect.callbacks, key=lambda x: x.callback_date)
    ]

    return ProspectDetailResponse(
        id=prospect.id,
        inspection_id=prospect.inspection_id,
        status=prospect.status.value if prospect.status else "new_lead",
        priority=prospect.priority,
        estimated_value=prospect.estimated_value,
        notes=prospect.notes,
        next_action=prospect.next_action,
        next_action_date=prospect.next_action_date,
        lost_reason=prospect.lost_reason,
        won_date=prospect.won_date,
        won_value=prospect.won_value,
        created_at=prospect.created_at,
        updated_at=prospect.updated_at,
        activity_nr=insp.activity_nr if insp else None,
        estab_name=insp.estab_name if insp else None,
        site_address=insp.site_address if insp else None,
        site_city=insp.site_city if insp else None,
        site_state=insp.site_state if insp else None,
        site_zip=insp.site_zip if insp else None,
        total_current_penalty=insp.total_current_penalty if insp else None,
        open_date=insp.open_date if insp else None,
        activity_count=len(prospect.activities),
        callback_count=len([c for c in prospect.callbacks if c.status == CallbackStatus.PENDING]),
        activities=activities,
        callbacks=callbacks,
    )


@router.post("/prospects", response_model=ProspectResponse)
async def create_prospect(
    request: CreateProspectRequest,
    db: Session = Depends(get_db),
):
    """Create a prospect from an inspection."""
    # Check if inspection exists
    inspection = db.execute(
        select(Inspection).where(Inspection.id == request.inspection_id)
    ).scalar()

    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    # Check if prospect already exists for this inspection
    existing = db.execute(
        select(Prospect).where(Prospect.inspection_id == request.inspection_id)
    ).scalar()

    if existing:
        raise HTTPException(status_code=400, detail="Prospect already exists for this inspection")

    # Create prospect
    prospect = Prospect(
        inspection_id=request.inspection_id,
        status=ProspectStatus(request.status) if request.status else ProspectStatus.NEW_LEAD,
        priority=request.priority,
        estimated_value=request.estimated_value,
        notes=request.notes,
        next_action=request.next_action,
        next_action_date=request.next_action_date,
    )
    db.add(prospect)
    db.commit()
    db.refresh(prospect)

    return ProspectResponse(
        id=prospect.id,
        inspection_id=prospect.inspection_id,
        status=prospect.status.value,
        priority=prospect.priority,
        estimated_value=prospect.estimated_value,
        notes=prospect.notes,
        next_action=prospect.next_action,
        next_action_date=prospect.next_action_date,
        lost_reason=prospect.lost_reason,
        won_date=prospect.won_date,
        won_value=prospect.won_value,
        created_at=prospect.created_at,
        updated_at=prospect.updated_at,
        activity_nr=inspection.activity_nr,
        estab_name=inspection.estab_name,
        site_address=inspection.site_address,
        site_city=inspection.site_city,
        site_state=inspection.site_state,
        site_zip=inspection.site_zip,
        total_current_penalty=inspection.total_current_penalty,
        open_date=inspection.open_date,
        activity_count=0,
        callback_count=0,
    )


@router.patch("/prospects/{prospect_id}", response_model=ProspectResponse)
async def update_prospect(
    prospect_id: int,
    request: UpdateProspectRequest,
    db: Session = Depends(get_db),
):
    """Update a prospect."""
    prospect = db.execute(
        select(Prospect).options(joinedload(Prospect.inspection)).where(Prospect.id == prospect_id)
    ).scalar()

    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    # Update fields
    if request.status is not None:
        prospect.status = ProspectStatus(request.status)
        # Auto-set won_date when status changes to WON
        if request.status == "won" and not prospect.won_date:
            prospect.won_date = date.today()
    if request.priority is not None:
        prospect.priority = request.priority
    if request.estimated_value is not None:
        prospect.estimated_value = request.estimated_value
    if request.notes is not None:
        prospect.notes = request.notes
    if request.next_action is not None:
        prospect.next_action = request.next_action
    if request.next_action_date is not None:
        prospect.next_action_date = request.next_action_date
    if request.lost_reason is not None:
        prospect.lost_reason = request.lost_reason
    if request.won_date is not None:
        prospect.won_date = request.won_date
    if request.won_value is not None:
        prospect.won_value = request.won_value

    prospect.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(prospect)

    insp = prospect.inspection

    # Get counts
    activity_count = db.execute(
        select(func.count(Activity.id)).where(Activity.prospect_id == prospect.id)
    ).scalar()
    callback_count = db.execute(
        select(func.count(Callback.id)).where(
            and_(Callback.prospect_id == prospect.id, Callback.status == CallbackStatus.PENDING)
        )
    ).scalar()

    return ProspectResponse(
        id=prospect.id,
        inspection_id=prospect.inspection_id,
        status=prospect.status.value,
        priority=prospect.priority,
        estimated_value=prospect.estimated_value,
        notes=prospect.notes,
        next_action=prospect.next_action,
        next_action_date=prospect.next_action_date,
        lost_reason=prospect.lost_reason,
        won_date=prospect.won_date,
        won_value=prospect.won_value,
        created_at=prospect.created_at,
        updated_at=prospect.updated_at,
        activity_nr=insp.activity_nr if insp else None,
        estab_name=insp.estab_name if insp else None,
        site_address=insp.site_address if insp else None,
        site_city=insp.site_city if insp else None,
        site_state=insp.site_state if insp else None,
        site_zip=insp.site_zip if insp else None,
        total_current_penalty=insp.total_current_penalty if insp else None,
        open_date=insp.open_date if insp else None,
        activity_count=activity_count,
        callback_count=callback_count,
    )


@router.delete("/prospects/{prospect_id}")
async def delete_prospect(
    prospect_id: int,
    db: Session = Depends(get_db),
):
    """Delete a prospect and all related activities/callbacks."""
    prospect = db.execute(
        select(Prospect).where(Prospect.id == prospect_id)
    ).scalar()

    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    db.delete(prospect)
    db.commit()

    return {"success": True, "message": "Prospect deleted"}


# =============================================================================
# ACTIVITY ENDPOINTS
# =============================================================================

@router.get("/prospects/{prospect_id}/activities", response_model=List[ActivityResponse])
async def list_activities(
    prospect_id: int,
    activity_type: Optional[str] = Query(None, description="Filter by activity type"),
    db: Session = Depends(get_db),
):
    """List activities for a prospect."""
    query = select(Activity).where(Activity.prospect_id == prospect_id)

    if activity_type:
        query = query.where(Activity.activity_type == activity_type)

    query = query.order_by(desc(Activity.activity_date))
    activities = db.execute(query).scalars().all()

    return [
        ActivityResponse(
            id=a.id,
            prospect_id=a.prospect_id,
            activity_type=a.activity_type.value if a.activity_type else None,
            subject=a.subject,
            description=a.description,
            outcome=a.outcome,
            activity_date=a.activity_date,
            duration_minutes=a.duration_minutes,
            task_due_date=a.task_due_date,
            task_completed=a.task_completed,
            task_completed_date=a.task_completed_date,
            created_at=a.created_at,
        )
        for a in activities
    ]


@router.post("/prospects/{prospect_id}/activities", response_model=ActivityResponse)
async def create_activity(
    prospect_id: int,
    request: CreateActivityRequest,
    db: Session = Depends(get_db),
):
    """Create an activity for a prospect."""
    # Verify prospect exists
    prospect = db.execute(
        select(Prospect).where(Prospect.id == prospect_id)
    ).scalar()

    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    activity = Activity(
        prospect_id=prospect_id,
        activity_type=ActivityType(request.activity_type),
        subject=request.subject,
        description=request.description,
        outcome=request.outcome,
        activity_date=request.activity_date or datetime.utcnow(),
        duration_minutes=request.duration_minutes,
        task_due_date=request.task_due_date,
    )
    db.add(activity)

    # Update prospect's updated_at and potentially status
    prospect.updated_at = datetime.utcnow()
    if prospect.status == ProspectStatus.NEW_LEAD and request.activity_type in ["call", "email", "meeting"]:
        prospect.status = ProspectStatus.CONTACTED

    db.commit()
    db.refresh(activity)

    return ActivityResponse(
        id=activity.id,
        prospect_id=activity.prospect_id,
        activity_type=activity.activity_type.value,
        subject=activity.subject,
        description=activity.description,
        outcome=activity.outcome,
        activity_date=activity.activity_date,
        duration_minutes=activity.duration_minutes,
        task_due_date=activity.task_due_date,
        task_completed=activity.task_completed,
        task_completed_date=activity.task_completed_date,
        created_at=activity.created_at,
    )


@router.patch("/activities/{activity_id}", response_model=ActivityResponse)
async def update_activity(
    activity_id: int,
    request: UpdateActivityRequest,
    db: Session = Depends(get_db),
):
    """Update an activity."""
    activity = db.execute(
        select(Activity).where(Activity.id == activity_id)
    ).scalar()

    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    if request.subject is not None:
        activity.subject = request.subject
    if request.description is not None:
        activity.description = request.description
    if request.outcome is not None:
        activity.outcome = request.outcome
    if request.task_completed is not None:
        activity.task_completed = request.task_completed
        if request.task_completed:
            activity.task_completed_date = datetime.utcnow()

    db.commit()
    db.refresh(activity)

    return ActivityResponse(
        id=activity.id,
        prospect_id=activity.prospect_id,
        activity_type=activity.activity_type.value if activity.activity_type else None,
        subject=activity.subject,
        description=activity.description,
        outcome=activity.outcome,
        activity_date=activity.activity_date,
        duration_minutes=activity.duration_minutes,
        task_due_date=activity.task_due_date,
        task_completed=activity.task_completed,
        task_completed_date=activity.task_completed_date,
        created_at=activity.created_at,
    )


@router.delete("/activities/{activity_id}")
async def delete_activity(
    activity_id: int,
    db: Session = Depends(get_db),
):
    """Delete an activity."""
    activity = db.execute(
        select(Activity).where(Activity.id == activity_id)
    ).scalar()

    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    db.delete(activity)
    db.commit()

    return {"success": True, "message": "Activity deleted"}


# =============================================================================
# CALLBACK ENDPOINTS
# =============================================================================

@router.get("/callbacks", response_model=List[CallbackResponse])
async def list_callbacks(
    status: Optional[str] = Query(None, description="Filter by status"),
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    db: Session = Depends(get_db),
):
    """List all callbacks with filters."""
    query = select(Callback).options(
        joinedload(Callback.prospect).joinedload(Prospect.inspection)
    )

    if status:
        query = query.where(Callback.status == status)
    if start_date:
        query = query.where(Callback.callback_date >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.where(Callback.callback_date <= datetime.combine(end_date, datetime.max.time()))

    query = query.order_by(Callback.callback_date)
    callbacks = db.execute(query).scalars().unique().all()

    return [
        CallbackResponse(
            id=c.id,
            prospect_id=c.prospect_id,
            callback_date=c.callback_date,
            callback_type=c.callback_type,
            notes=c.notes,
            status=c.status.value if c.status else "pending",
            completed_at=c.completed_at,
            created_at=c.created_at,
            estab_name=c.prospect.inspection.estab_name if c.prospect and c.prospect.inspection else None,
            site_state=c.prospect.inspection.site_state if c.prospect and c.prospect.inspection else None,
        )
        for c in callbacks
    ]


@router.get("/callbacks/upcoming", response_model=List[CallbackResponse])
async def list_upcoming_callbacks(
    days: int = Query(7, description="Number of days to look ahead"),
    db: Session = Depends(get_db),
):
    """Get upcoming callbacks for dashboard widget."""
    now = datetime.utcnow()
    end_date = now + timedelta(days=days)

    callbacks = db.execute(
        select(Callback)
        .options(joinedload(Callback.prospect).joinedload(Prospect.inspection))
        .where(
            and_(
                Callback.status == CallbackStatus.PENDING,
                Callback.callback_date >= now,
                Callback.callback_date <= end_date,
            )
        )
        .order_by(Callback.callback_date)
    ).scalars().unique().all()

    return [
        CallbackResponse(
            id=c.id,
            prospect_id=c.prospect_id,
            callback_date=c.callback_date,
            callback_type=c.callback_type,
            notes=c.notes,
            status=c.status.value if c.status else "pending",
            completed_at=c.completed_at,
            created_at=c.created_at,
            estab_name=c.prospect.inspection.estab_name if c.prospect and c.prospect.inspection else None,
            site_state=c.prospect.inspection.site_state if c.prospect and c.prospect.inspection else None,
        )
        for c in callbacks
    ]


@router.post("/prospects/{prospect_id}/callbacks", response_model=CallbackResponse)
async def create_callback(
    prospect_id: int,
    request: CreateCallbackRequest,
    db: Session = Depends(get_db),
):
    """Schedule a callback for a prospect."""
    prospect = db.execute(
        select(Prospect).options(joinedload(Prospect.inspection)).where(Prospect.id == prospect_id)
    ).scalar()

    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    callback = Callback(
        prospect_id=prospect_id,
        callback_date=request.callback_date,
        callback_type=request.callback_type,
        notes=request.notes,
    )
    db.add(callback)

    # Update prospect's next_action if this callback is sooner
    if not prospect.next_action_date or request.callback_date.date() < prospect.next_action_date:
        prospect.next_action_date = request.callback_date.date()
        prospect.next_action = f"{request.callback_type or 'Follow-up'}: {request.notes[:50] if request.notes else 'Scheduled callback'}"

    db.commit()
    db.refresh(callback)

    return CallbackResponse(
        id=callback.id,
        prospect_id=callback.prospect_id,
        callback_date=callback.callback_date,
        callback_type=callback.callback_type,
        notes=callback.notes,
        status=callback.status.value,
        completed_at=callback.completed_at,
        created_at=callback.created_at,
        estab_name=prospect.inspection.estab_name if prospect.inspection else None,
        site_state=prospect.inspection.site_state if prospect.inspection else None,
    )


@router.patch("/callbacks/{callback_id}", response_model=CallbackResponse)
async def update_callback(
    callback_id: int,
    request: UpdateCallbackRequest,
    db: Session = Depends(get_db),
):
    """Update a callback."""
    callback = db.execute(
        select(Callback).options(
            joinedload(Callback.prospect).joinedload(Prospect.inspection)
        ).where(Callback.id == callback_id)
    ).scalar()

    if not callback:
        raise HTTPException(status_code=404, detail="Callback not found")

    if request.callback_date is not None:
        callback.callback_date = request.callback_date
    if request.callback_type is not None:
        callback.callback_type = request.callback_type
    if request.notes is not None:
        callback.notes = request.notes
    if request.status is not None:
        callback.status = CallbackStatus(request.status)
        if request.status == "completed":
            callback.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(callback)

    return CallbackResponse(
        id=callback.id,
        prospect_id=callback.prospect_id,
        callback_date=callback.callback_date,
        callback_type=callback.callback_type,
        notes=callback.notes,
        status=callback.status.value if callback.status else "pending",
        completed_at=callback.completed_at,
        created_at=callback.created_at,
        estab_name=callback.prospect.inspection.estab_name if callback.prospect and callback.prospect.inspection else None,
        site_state=callback.prospect.inspection.site_state if callback.prospect and callback.prospect.inspection else None,
    )


@router.delete("/callbacks/{callback_id}")
async def delete_callback(
    callback_id: int,
    db: Session = Depends(get_db),
):
    """Delete a callback."""
    callback = db.execute(
        select(Callback).where(Callback.id == callback_id)
    ).scalar()

    if not callback:
        raise HTTPException(status_code=404, detail="Callback not found")

    db.delete(callback)
    db.commit()

    return {"success": True, "message": "Callback deleted"}


# =============================================================================
# STATS ENDPOINT
# =============================================================================

@router.get("/stats", response_model=CRMStatsResponse)
async def get_crm_stats(
    db: Session = Depends(get_db),
):
    """Get CRM dashboard statistics."""
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)

    # Total prospects
    total_prospects = db.execute(
        select(func.count(Prospect.id))
    ).scalar() or 0

    # By status
    status_counts = db.execute(
        select(Prospect.status, func.count(Prospect.id))
        .group_by(Prospect.status)
    ).all()
    by_status = {s.value if s else "unknown": c for s, c in status_counts}

    # Upcoming callbacks (next 7 days)
    upcoming_callbacks = db.execute(
        select(func.count(Callback.id)).where(
            and_(
                Callback.status == CallbackStatus.PENDING,
                Callback.callback_date >= now,
                Callback.callback_date <= now + timedelta(days=7),
            )
        )
    ).scalar() or 0

    # Overdue callbacks
    overdue_callbacks = db.execute(
        select(func.count(Callback.id)).where(
            and_(
                Callback.status == CallbackStatus.PENDING,
                Callback.callback_date < now,
            )
        )
    ).scalar() or 0

    # Tasks due today
    today = date.today()
    tasks_due_today = db.execute(
        select(func.count(Activity.id)).where(
            and_(
                Activity.activity_type == ActivityType.TASK,
                Activity.task_due_date == today,
                Activity.task_completed == False,
            )
        )
    ).scalar() or 0

    # Total pipeline value (non-won/lost prospects)
    total_pipeline_value = db.execute(
        select(func.coalesce(func.sum(Prospect.estimated_value), 0)).where(
            Prospect.status.in_([ProspectStatus.NEW_LEAD, ProspectStatus.CONTACTED, ProspectStatus.QUALIFIED])
        )
    ).scalar() or 0

    # Won this month
    won_this_month = db.execute(
        select(func.count(Prospect.id)).where(
            and_(
                Prospect.status == ProspectStatus.WON,
                Prospect.won_date >= month_start.date(),
            )
        )
    ).scalar() or 0

    # Won value this month
    won_value_this_month = db.execute(
        select(func.coalesce(func.sum(Prospect.won_value), 0)).where(
            and_(
                Prospect.status == ProspectStatus.WON,
                Prospect.won_date >= month_start.date(),
            )
        )
    ).scalar() or 0

    return CRMStatsResponse(
        total_prospects=total_prospects,
        by_status=by_status,
        upcoming_callbacks=upcoming_callbacks,
        overdue_callbacks=overdue_callbacks,
        tasks_due_today=tasks_due_today,
        total_pipeline_value=total_pipeline_value,
        won_this_month=won_this_month,
        won_value_this_month=won_value_this_month,
    )


# =============================================================================
# UTILITY ENDPOINTS
# =============================================================================

@router.get("/inspection/{inspection_id}/prospect")
async def get_prospect_by_inspection(
    inspection_id: int,
    db: Session = Depends(get_db),
):
    """Check if a prospect exists for an inspection."""
    prospect = db.execute(
        select(Prospect).where(Prospect.inspection_id == inspection_id)
    ).scalar()

    if prospect:
        return {
            "exists": True,
            "id": prospect.id,
            "status": prospect.status.value if prospect.status else "new_lead",
            "priority": prospect.priority,
        }
    return {"exists": False, "id": None}
