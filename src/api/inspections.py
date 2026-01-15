from datetime import date
from typing import Optional, List
import asyncio
import time

from fastapi import APIRouter, Depends, Query, HTTPException, Header, Request
from fastapi.responses import StreamingResponse, HTMLResponse
import json
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, or_
from pydantic import BaseModel

from src.database.connection import get_db, get_db_session
from src.database.models import Inspection, Violation, EnrichmentStatus, Company, Contact, CronRun
from src.services.sync_service import sync_service
from src.services.web_enrichment import web_enrichment_service
from src.config import settings

router = APIRouter()


def _verify_cron_secret(x_cron_secret: Optional[str]) -> None:
    if settings.CRON_SECRET and x_cron_secret != settings.CRON_SECRET:
        raise HTTPException(status_code=401, detail="Invalid cron secret")


def _start_cron_run(db: Session, job_name: str) -> CronRun:
    run = CronRun(job_name=job_name, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _finish_cron_run(db: Session, run: CronRun, status: str, details: Optional[str] = None, error: Optional[str] = None) -> None:
    from datetime import datetime

    run.status = status
    run.finished_at = datetime.utcnow()
    run.details = details
    run.error = error
    db.commit()


def _format_dt(dt_value):
    if not dt_value:
        return None
    return f"{dt_value.isoformat()}Z"


class ViolationResponse(BaseModel):
    """Response model for violation data."""
    id: int
    activity_nr: str
    citation_id: str
    standard: Optional[str]
    viol_type: Optional[str]
    issuance_date: Optional[date]
    abate_date: Optional[date]
    current_penalty: Optional[float]
    initial_penalty: Optional[float]
    nr_instances: Optional[int]
    nr_exposed: Optional[int]
    gravity: Optional[str]

    model_config = {"from_attributes": True}


class InspectionResponse(BaseModel):
    """Response model for inspection data."""
    id: int
    activity_nr: str
    estab_name: str
    site_address: Optional[str]
    site_city: Optional[str]
    site_state: Optional[str]
    site_zip: Optional[str]
    open_date: Optional[date]
    close_conf_date: Optional[date]
    close_case_date: Optional[date]
    sic_code: Optional[str]
    naics_code: Optional[str]
    insp_type: Optional[str]
    insp_scope: Optional[str]
    total_current_penalty: Optional[float]
    total_initial_penalty: Optional[float]
    violation_count: int = 0
    owner_type: Optional[str]
    nr_in_estab: Optional[int] = None
    enrichment_status: EnrichmentStatus

    model_config = {"from_attributes": True, "use_enum_values": True}


class InspectionDetailResponse(InspectionResponse):
    """Response model for inspection with violations."""
    violations: List[ViolationResponse] = []

    model_config = {"from_attributes": True, "use_enum_values": True}


class InspectionListResponse(BaseModel):
    """Paginated list response."""
    items: List[InspectionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SyncResponse(BaseModel):
    """Response model for sync operation."""
    fetched: int
    created: int
    updated: int
    skipped_old: int = 0
    skipped_state: int = 0
    errors: int
    logs: List[str] = []  # Detailed log messages for debugging


class StatsResponse(BaseModel):
    """Response model for statistics."""
    total_inspections: int
    total_penalties: float
    states_count: int
    avg_penalty: float
    inspections_by_state: dict
    inspections_by_type: dict


class NewViolationsItem(BaseModel):
    """Item in new violations list."""
    inspection_id: int
    activity_nr: str
    estab_name: str
    site_city: Optional[str]
    site_state: Optional[str]
    violation_count: int
    issuance_date: str
    total_current_penalty: float

    class Config:
        from_attributes = True


class NewViolationsResponse(BaseModel):
    """Response model for new violations widget."""
    count: int
    total_companies: int
    total_penalties: float
    items: List[NewViolationsItem]


@router.get("", response_model=InspectionListResponse)
async def list_inspections(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    state: Optional[str] = Query(None, description="Filter by state (2-letter code)"),
    city: Optional[str] = Query(None, description="Filter by city"),
    search: Optional[str] = Query(None, description="Search establishment name"),
    activity_nr: Optional[str] = Query(None, description="Filter by activity number"),
    min_penalty: Optional[float] = Query(None, description="Minimum penalty amount"),
    max_penalty: Optional[float] = Query(None, description="Maximum penalty amount"),
    start_date: Optional[date] = Query(None, description="Filter by open date (start)"),
    end_date: Optional[date] = Query(None, description="Filter by open date (end)"),
    insp_type: Optional[str] = Query(None, description="Filter by inspection type"),
    has_violations: Optional[bool] = Query(None, description="Filter by whether inspection has violations"),
    multiple_inspections: Optional[bool] = Query(None, description="Filter for companies with multiple inspections"),
    sort_by: str = Query("open_date", description="Sort field"),
    sort_desc: bool = Query(True, description="Sort descending"),
    db: Session = Depends(get_db),
):
    """
    List inspections with filtering and pagination.
    """
    # Simple query - no subqueries for maximum speed
    # Violation count will be 0 in list view (calculated only in detail view)
    query = select(Inspection)

    # Apply filters
    if state:
        query = query.where(Inspection.site_state == state.upper())

    if city:
        query = query.where(Inspection.site_city.ilike(f"%{city}%"))

    if search:
        query = query.where(Inspection.estab_name.ilike(f"%{search}%"))

    if activity_nr:
        query = query.where(Inspection.activity_nr.ilike(f"%{activity_nr}%"))

    if start_date:
        query = query.where(Inspection.open_date >= start_date)

    if end_date:
        query = query.where(Inspection.open_date <= end_date)

    if insp_type:
        query = query.where(Inspection.insp_type == insp_type)

    # Filter by penalty using stored penalty values (much faster)
    if min_penalty is not None:
        query = query.where(Inspection.total_current_penalty >= min_penalty)

    if max_penalty is not None:
        query = query.where(Inspection.total_current_penalty <= max_penalty)

    # Filter by has violations (use penalty as proxy - faster than counting violations)
    if has_violations is True:
        query = query.where(Inspection.total_current_penalty > 0)
    elif has_violations is False:
        query = query.where(or_(
            Inspection.total_current_penalty.is_(None),
            Inspection.total_current_penalty == 0
        ))

    # Filter for companies with multiple inspections
    if multiple_inspections is True:
        # Subquery to find company names that appear more than once
        company_count_subquery = (
            select(
                Inspection.estab_name,
                func.count(Inspection.id).label('inspection_count')
            )
            .group_by(Inspection.estab_name)
            .having(func.count(Inspection.id) > 1)
            .subquery()
        )
        # Join to filter only inspections whose company name appears multiple times
        query = query.join(
            company_count_subquery,
            Inspection.estab_name == company_count_subquery.c.estab_name
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar()

    # Apply sorting
    if sort_by == 'violation_count':
        # Use penalty as proxy for violation count (faster)
        sort_column = Inspection.total_current_penalty
    elif sort_by == 'total_current_penalty':
        sort_column = Inspection.total_current_penalty
    else:
        sort_column = getattr(Inspection, sort_by, Inspection.open_date)

    if sort_desc:
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(sort_column)

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query - returns Inspection objects directly
    results = db.execute(query).scalars().all()

    # Batch fetch violation counts for just this page's inspections (fast - single query)
    activity_nrs = [r.activity_nr for r in results]
    violation_counts = {}
    if activity_nrs:
        count_query = (
            select(Violation.activity_nr, func.count(Violation.id))
            .where(Violation.activity_nr.in_(activity_nrs))
            .group_by(Violation.activity_nr)
        )
        for activity_nr, count in db.execute(count_query).all():
            violation_counts[activity_nr] = count

    # Map results to response with violation counts
    items = []
    for inspection in results:
        inspection.violation_count = violation_counts.get(inspection.activity_nr, 0)
        items.append(inspection)

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return InspectionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def _build_inspection_filters(
    state: Optional[str] = None,
    city: Optional[str] = None,
    search: Optional[str] = None,
    activity_nr: Optional[str] = None,
    min_penalty: Optional[float] = None,
    max_penalty: Optional[float] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    insp_type: Optional[str] = None,
):
    """Build filter conditions for inspection queries."""
    conditions = []
    if state:
        conditions.append(Inspection.site_state == state.upper())
    if city:
        conditions.append(Inspection.site_city.ilike(f"%{city}%"))
    if search:
        conditions.append(Inspection.estab_name.ilike(f"%{search}%"))
    if activity_nr:
        conditions.append(Inspection.activity_nr.ilike(f"%{activity_nr}%"))
    if min_penalty is not None:
        conditions.append(Inspection.total_current_penalty >= min_penalty)
    if max_penalty is not None:
        conditions.append(Inspection.total_current_penalty <= max_penalty)
    if start_date:
        conditions.append(Inspection.open_date >= start_date)
    if end_date:
        conditions.append(Inspection.open_date <= end_date)
    if insp_type:
        conditions.append(Inspection.insp_type == insp_type)
    return conditions


class DateRangeResponse(BaseModel):
    """Response for available data date range."""
    earliest_date: Optional[str]
    latest_date: Optional[str]
    total_records: int


@router.get("/date-range", response_model=DateRangeResponse)
async def get_date_range(db: Session = Depends(get_db)):
    """Get the date range of all available inspection data."""
    from sqlalchemy import func

    result = db.execute(
        select(
            func.min(Inspection.open_date),
            func.max(Inspection.open_date),
            func.count(Inspection.id)
        )
    ).one()

    earliest = result[0]
    latest = result[1]
    total = result[2] or 0

    return DateRangeResponse(
        earliest_date=earliest.isoformat() if earliest else None,
        latest_date=latest.isoformat() if latest else None,
        total_records=total
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    state: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    activity_nr: Optional[str] = Query(None),
    min_penalty: Optional[float] = Query(None),
    max_penalty: Optional[float] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    insp_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get inspection statistics based on current filters."""
    conditions = _build_inspection_filters(
        state, city, search, activity_nr, min_penalty, max_penalty, start_date, end_date, insp_type
    )

    # Single query to get all stats from inspections table (fast - uses stored penalty values)
    stats_query = select(
        func.count(Inspection.id),
        func.coalesce(func.sum(Inspection.total_current_penalty), 0),
        func.count(func.distinct(Inspection.site_state)),
        func.count(Inspection.id).filter(Inspection.total_current_penalty > 0)
    )
    if conditions:
        stats_query = stats_query.where(*conditions)

    result = db.execute(stats_query).one()
    total = result[0]
    total_penalties = float(result[1])
    states_count = result[2]
    inspections_with_violations = result[3]

    # Average penalty per inspection with violations
    avg_penalty = total_penalties / inspections_with_violations if inspections_with_violations > 0 else 0

    # Inspections by state (top 10) - from filtered results
    state_query = (
        select(Inspection.site_state, func.count(Inspection.id))
        .where(Inspection.site_state.isnot(None))
        .group_by(Inspection.site_state)
        .order_by(desc(func.count(Inspection.id)))
        .limit(10)
    )
    if conditions:
        state_query = state_query.where(*conditions)
    state_counts = db.execute(state_query).all()
    inspections_by_state = {s: c for s, c in state_counts if s}

    # Inspections by type - from filtered results
    type_query = (
        select(Inspection.insp_type, func.count(Inspection.id))
        .group_by(Inspection.insp_type)
        .order_by(desc(func.count(Inspection.id)))
    )
    if conditions:
        type_query = type_query.where(*conditions)
    type_counts = db.execute(type_query).all()
    inspections_by_type = {t or "Unknown": c for t, c in type_counts}

    return StatsResponse(
        total_inspections=total,
        total_penalties=total_penalties,
        states_count=states_count,
        avg_penalty=float(avg_penalty),
        inspections_by_state=inspections_by_state,
        inspections_by_type=inspections_by_type,
    )


@router.get("/violations/recent", response_model=NewViolationsResponse)
async def get_recent_violations(
    days: int = Query(45, ge=1, le=365, description="Look back N days"),
    state: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    insp_type: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    """Get violations issued in the last N days."""
    from datetime import date as dt_date, timedelta

    cutoff_date = dt_date.today() - timedelta(days=days)

    # Single query with JOIN to get violations with inspection details
    query = (
        select(
            Inspection.id,
            Inspection.activity_nr,
            Inspection.estab_name,
            Inspection.site_city,
            Inspection.site_state,
            Inspection.insp_type,
            Inspection.open_date,
            func.count(Violation.id).label('violation_count'),
            func.max(Violation.issuance_date).label('latest_issuance'),
            func.coalesce(func.sum(Violation.current_penalty), 0).label('total_penalty')
        )
        .join(Violation, Inspection.activity_nr == Violation.activity_nr)
        .where(Violation.issuance_date >= cutoff_date)
        .group_by(
            Inspection.id,
            Inspection.activity_nr,
            Inspection.estab_name,
            Inspection.site_city,
            Inspection.site_state,
            Inspection.insp_type,
            Inspection.open_date
        )
    )

    # Apply filters
    if state:
        query = query.where(Inspection.site_state == state.upper())
    if search:
        query = query.where(Inspection.estab_name.ilike(f"%{search}%"))
    if insp_type:
        query = query.where(Inspection.insp_type == insp_type)
    if start_date:
        query = query.where(Inspection.open_date >= start_date)
    if end_date:
        query = query.where(Inspection.open_date <= end_date)

    # Order by most recent violation first
    query = query.order_by(desc('latest_issuance'))

    results = db.execute(query).all()

    # Build response
    items = []
    total_penalties = 0.0
    total_violation_count = 0

    for row in results:
        total_penalties += float(row.total_penalty)
        total_violation_count += row.violation_count
        items.append(NewViolationsItem(
            inspection_id=row.id,
            activity_nr=row.activity_nr,
            estab_name=row.estab_name,
            site_city=row.site_city,
            site_state=row.site_state,
            violation_count=row.violation_count,
            issuance_date=row.latest_issuance.isoformat() if row.latest_issuance else '',
            total_current_penalty=float(row.total_penalty)
        ))

    return NewViolationsResponse(
        count=total_violation_count,
        total_companies=len(items),
        total_penalties=total_penalties,
        items=items
    )


@router.get("/recent")
async def get_recent_inspections(
    days: int = Query(7, ge=1, le=90, description="Look back N days"),
    state: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    insp_type: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    """Get inspections opened in the last N days (by open_date), with optional filters."""
    from datetime import date as dt_date, timedelta

    cutoff_date = dt_date.today() - timedelta(days=days)

    # Build query with filters
    query = select(Inspection).where(
        Inspection.open_date.isnot(None),
        Inspection.open_date >= cutoff_date
    )

    # Apply filters
    if state:
        query = query.where(Inspection.site_state == state.upper())

    if search:
        query = query.where(Inspection.estab_name.ilike(f"%{search}%"))

    if insp_type:
        query = query.where(Inspection.insp_type == insp_type)

    if start_date:
        query = query.where(Inspection.open_date >= start_date)

    if end_date:
        query = query.where(Inspection.open_date <= end_date)

    query = query.order_by(desc(Inspection.open_date))

    # Get inspections
    inspections = db.execute(query).scalars().all()

    # Build items list
    items = []
    for inspection in inspections:
        items.append({
            "inspection_id": inspection.id,
            "activity_nr": inspection.activity_nr,
            "estab_name": inspection.estab_name,
            "site_city": inspection.site_city,
            "site_state": inspection.site_state,
            "insp_type": inspection.insp_type,
            "open_date": inspection.open_date.isoformat() if inspection.open_date else None,
            "total_current_penalty": inspection.total_current_penalty or 0,
        })

    return {
        "count": len(items),
        "unique_companies": len(set(i["estab_name"] for i in items)),
        "items": items
    }


@router.get("/states")
async def get_states(db: Session = Depends(get_db)):
    """Get list of all states with inspections."""
    results = db.execute(
        select(Inspection.site_state, func.count(Inspection.id))
        .where(Inspection.site_state.isnot(None))
        .group_by(Inspection.site_state)
        .order_by(Inspection.site_state)
    ).all()

    return [{"state": state, "count": count} for state, count in results]


@router.get("/types")
async def get_inspection_types(db: Session = Depends(get_db)):
    """Get list of all inspection types."""
    results = db.execute(
        select(Inspection.insp_type, func.count(Inspection.id))
        .where(Inspection.insp_type.isnot(None))
        .group_by(Inspection.insp_type)
        .order_by(Inspection.insp_type)
    ).all()

    return [{"type": insp_type, "count": count} for insp_type, count in results]


class RelatedInspectionResponse(BaseModel):
    """Response model for related inspection summary."""
    id: int
    activity_nr: str
    open_date: Optional[date]
    site_city: Optional[str]
    site_state: Optional[str]
    insp_type: Optional[str]
    total_current_penalty: float = 0
    violation_count: int = 0

    class Config:
        from_attributes = True


@router.get("/{inspection_id}/related", response_model=List[RelatedInspectionResponse])
async def get_related_inspections(inspection_id: int, db: Session = Depends(get_db)):
    """Get other inspections for the same company."""
    # First get the inspection to find the company name
    inspection = db.execute(
        select(Inspection).where(Inspection.id == inspection_id)
    ).scalar_one_or_none()

    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    # Subquery to get penalty sums and violation count
    penalty_subquery = (
        select(
            Violation.activity_nr,
            func.coalesce(func.sum(Violation.current_penalty), 0).label('current_penalty_sum'),
            func.count(Violation.id).label('violation_count')
        )
        .group_by(Violation.activity_nr)
        .subquery()
    )

    # Find other inspections with the same establishment name (excluding current)
    results = db.execute(
        select(
            Inspection,
            func.coalesce(penalty_subquery.c.current_penalty_sum, 0).label('calculated_penalty'),
            func.coalesce(penalty_subquery.c.violation_count, 0).label('viol_count')
        )
        .outerjoin(penalty_subquery, Inspection.activity_nr == penalty_subquery.c.activity_nr)
        .where(Inspection.estab_name == inspection.estab_name)
        .where(Inspection.id != inspection_id)
        .order_by(desc(Inspection.open_date))
        .limit(10)
    ).all()

    related = []
    for row in results:
        insp = row[0]
        related.append(RelatedInspectionResponse(
            id=insp.id,
            activity_nr=insp.activity_nr,
            open_date=insp.open_date,
            site_city=insp.site_city,
            site_state=insp.site_state,
            insp_type=insp.insp_type,
            total_current_penalty=row[1] or 0,
            violation_count=row[2] or 0
        ))

    return related


@router.get("/{inspection_id}", response_model=InspectionDetailResponse)
async def get_inspection(inspection_id: int, db: Session = Depends(get_db)):
    """Get a single inspection by ID with violations."""
    inspection = db.execute(
        select(Inspection).where(Inspection.id == inspection_id)
    ).scalar_one_or_none()

    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    # Get violations for this inspection
    violations = db.execute(
        select(Violation)
        .where(Violation.activity_nr == inspection.activity_nr)
        .order_by(desc(Violation.current_penalty))
    ).scalars().all()

    # Calculate penalties from violations
    total_current = sum(v.current_penalty or 0 for v in violations)
    total_initial = sum(v.initial_penalty or 0 for v in violations)

    return InspectionDetailResponse(
        id=inspection.id,
        activity_nr=inspection.activity_nr,
        estab_name=inspection.estab_name,
        site_address=inspection.site_address,
        site_city=inspection.site_city,
        site_state=inspection.site_state,
        site_zip=inspection.site_zip,
        open_date=inspection.open_date,
        close_conf_date=inspection.close_conf_date,
        close_case_date=inspection.close_case_date,
        sic_code=inspection.sic_code,
        naics_code=inspection.naics_code,
        insp_type=inspection.insp_type,
        insp_scope=inspection.insp_scope,
        total_current_penalty=total_current,
        total_initial_penalty=total_initial,
        owner_type=inspection.owner_type,
        nr_in_estab=inspection.nr_in_estab,
        enrichment_status=inspection.enrichment_status,
        violations=violations,
    )


@router.post("/sync", response_model=SyncResponse)
async def trigger_sync(
    days_back: int = Query(30, ge=1, le=365),
    max_requests: int = Query(2, ge=1, le=50, description="Max API requests (default 2 for Vercel timeout + rate limits)")
):
    """
    Manually trigger a sync of OSHA inspection data.

    Note: Vercel has a 10-second timeout on Hobby plan. Default is 2 requests
    (400 records max) with 1.5s delay between requests to avoid DOL rate limits.
    Call multiple times for more data.
    """
    stats = await sync_service.sync_inspections(days_back=days_back, max_requests=max_requests)
    return SyncResponse(**stats)


@router.get("/cron/inspections", response_model=SyncResponse)
async def cron_sync_inspections(
    days_back: int = Query(30, ge=1, le=365, description="Days back to sync"),
    max_requests: int = Query(2, ge=1, le=50, description="Max API requests per run (default 2 for Vercel timeout)"),
    x_cron_secret: Optional[str] = Header(None),
):
    """
    Cron-triggered inspection sync (Vercel-friendly).

    Uses the same SyncService as the manual /sync endpoint for consistency.
    Default is 2 requests (400 records max) to stay within Vercel timeout.
    """
    _verify_cron_secret(x_cron_secret)

    # Use context manager for cron tracking to avoid connection pool exhaustion
    with get_db_session() as db:
        run = _start_cron_run(db, "inspections")
        run_id = run.id  # Save ID before session closes

    try:
        stats = await sync_service.sync_inspections(days_back=days_back, max_requests=max_requests)
        with get_db_session() as db:
            # Re-fetch the run since we're in a new session
            run = db.execute(select(CronRun).where(CronRun.id == run_id)).scalar_one()
            _finish_cron_run(db, run, "success", details=json.dumps(stats))
        return SyncResponse(**stats)
    except Exception as exc:
        with get_db_session() as db:
            run = db.execute(select(CronRun).where(CronRun.id == run_id)).scalar_one()
            _finish_cron_run(db, run, "failed", error=str(exc))
        raise

@router.get("/sync/status")
async def get_sync_status():
    """Get current sync status."""
    return await sync_service.get_sync_status()


@router.get("/sync/test-dol-api")
async def test_dol_api():
    """
    Test DOL API connectivity directly.
    Returns diagnostic info about the API connection.
    """
    import httpx
    from src.config import settings
    from datetime import datetime, timedelta
    import json

    results = {
        "timestamp": datetime.now().isoformat(),
        "api_key_configured": bool(settings.DOL_API_KEY),
        "api_key_preview": settings.DOL_API_KEY[:8] + "..." if settings.DOL_API_KEY else None,
        "tests": []
    }

    # Test 1: Simple request without filter
    try:
        url = "https://apiprod.dol.gov/v4/get/OSHA/inspection/json"
        params = {
            "X-API-KEY": settings.DOL_API_KEY,
            "limit": 1,
            "offset": 0
        }
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.get(url, params=params)
            results["tests"].append({
                "name": "Simple request (limit=1)",
                "url": url,
                "status_code": response.status_code,
                "response_length": len(response.text),
                "response_preview": response.text[:500] if response.text else None,
                "success": response.status_code == 200
            })
    except Exception as e:
        results["tests"].append({
            "name": "Simple request (limit=1)",
            "error": f"{type(e).__name__}: {str(e)}",
            "success": False
        })

    # Test 2: Request with date filter
    try:
        since_date = (datetime.now() - timedelta(days=30)).date()
        date_str = since_date.strftime("%m/%d/%Y")
        filter_object = {
            "field": "open_date",
            "operator": "gt",
            "value": date_str
        }
        url = "https://apiprod.dol.gov/v4/get/OSHA/inspection/json"
        params = {
            "X-API-KEY": settings.DOL_API_KEY,
            "limit": 5,
            "offset": 0,
            "filter_object": json.dumps(filter_object)
        }
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.get(url, params=params)
            results["tests"].append({
                "name": f"Filtered request (open_date > {date_str})",
                "url": url,
                "filter": filter_object,
                "status_code": response.status_code,
                "response_length": len(response.text),
                "response_preview": response.text[:500] if response.text else None,
                "success": response.status_code == 200
            })
    except Exception as e:
        results["tests"].append({
            "name": "Filtered request",
            "error": f"{type(e).__name__}: {str(e)}",
            "success": False
        })

    return results


@router.get("/sync/debug/{activity_nr}")
async def debug_fetch_inspection(activity_nr: str):
    """
    Debug endpoint: Fetch a specific inspection directly from DOL API.
    Use this to verify if an inspection exists in the API.
    """
    import httpx
    import json
    from src.config import settings

    results = {
        "activity_nr": activity_nr,
        "found_in_api": False,
        "found_in_db": False,
        "api_data": None,
        "db_data": None,
        "would_be_filtered": None,
        "filter_reason": None,
    }

    # Check if it exists in our database
    with get_db_session() as db:
        existing = db.execute(
            select(Inspection).where(Inspection.activity_nr == activity_nr)
        ).scalar_one_or_none()
        if existing:
            results["found_in_db"] = True
            results["db_data"] = {
                "id": existing.id,
                "activity_nr": existing.activity_nr,
                "estab_name": existing.estab_name,
                "site_state": existing.site_state,
                "site_city": existing.site_city,
                "open_date": existing.open_date.isoformat() if existing.open_date else None,
            }

    # Fetch directly from DOL API
    try:
        filter_object = {
            "field": "activity_nr",
            "operator": "eq",
            "value": activity_nr
        }
        url = "https://apiprod.dol.gov/v4/get/OSHA/inspection/json"
        params = {
            "X-API-KEY": settings.DOL_API_KEY,
            "limit": 1,
            "filter_object": json.dumps(filter_object),
        }

        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.get(url, params=params)
            results["api_status"] = response.status_code

            if response.status_code == 200 and response.text:
                data = response.json()
                records = data.get("data", []) if isinstance(data, dict) else data
                if records:
                    results["found_in_api"] = True
                    results["api_data"] = records[0]

                    # Check if it would be filtered
                    site_state = records[0].get("site_state", "")
                    open_date = records[0].get("open_date", "")

                    se_states = {"AL", "AR", "FL", "GA", "KY", "LA", "MS", "NC", "SC", "TN", "VA", "WV"}
                    if site_state and site_state.upper() not in se_states:
                        results["would_be_filtered"] = True
                        results["filter_reason"] = f"State '{site_state}' not in SE states"
                    else:
                        results["would_be_filtered"] = False
                else:
                    results["api_response"] = "No records returned"
            elif response.status_code == 204:
                results["api_response"] = "204 No Content - inspection not found in API"
            else:
                results["api_response"] = response.text[:500]

    except Exception as e:
        results["api_error"] = f"{type(e).__name__}: {str(e)}"

    return results


class ViolationSyncResponse(BaseModel):
    """Response model for violation sync operation."""
    inspections_checked: int
    inspections_with_new_violations: int
    new_violations_found: int
    updated_violations: int
    errors: int
    skipped: int


class ViolationSyncResponseWithLogs(ViolationSyncResponse):
    """Response model for violation sync with logs."""
    logs: List[str] = []


class RecentViolationsSyncResponse(BaseModel):
    """Response model for recent violations sync operation."""
    inspections_checked: int
    violations_fetched: int
    violations_inserted: int
    violations_updated: int
    inspections_with_new_violations: int
    errors: int
    logs: List[str] = []


class BulkViolationsSyncResponse(BaseModel):
    """Response model for bulk violations sync operation."""
    violations_fetched: int
    violations_inserted: int
    violations_updated: int
    violations_skipped: int
    inspections_with_new_violations: int
    errors: int
    logs: List[str] = []


@router.post("/sync/violations", response_model=ViolationSyncResponseWithLogs)
async def trigger_violation_sync(
    max_inspections: int = Query(3, ge=1, le=500, description="Max inspections to check (default 3 for Vercel timeout)"),
    days_back: int = Query(180, ge=30, le=365, description="How far back to check inspections (days)"),
    min_days_between_checks: int = Query(7, ge=1, le=90, description="Skip inspections checked within this window"),
    max_requests: int = Query(10, ge=1, le=50, description="Max API requests per run"),
):
    """
    Manually trigger a violation sync for existing inspections.

    This checks existing inspections for NEW violations that may have been issued.
    Focuses on inspections in the citation window (3-9 months old).

    Note: Vercel has 10-second timeout. Default is 3 inspections with 1.5s delay.
    Call multiple times for more coverage.
    """
    from src.services.violation_sync_service import violation_sync_service

    stats = await violation_sync_service.sync_violations_smart(
        max_inspections_to_check=max_inspections,
        rate_limit_delay=1.5,  # Match the inspection sync delay
        days_back=days_back,
        min_days_between_checks=min_days_between_checks,
        max_requests=max_requests,
    )
    return ViolationSyncResponseWithLogs(**stats)


@router.get("/cron/violations", response_model=ViolationSyncResponseWithLogs)
async def cron_sync_violations(
    max_inspections: int = Query(3, ge=1, le=500, description="Max inspections to check (default 3 for Vercel timeout)"),
    days_back: int = Query(180, ge=30, le=365, description="How far back to check inspections (days)"),
    min_days_between_checks: int = Query(7, ge=1, le=90, description="Skip inspections checked within this window"),
    max_requests: int = Query(10, ge=1, le=50, description="Max API requests per run"),
    x_cron_secret: Optional[str] = Header(None),
):
    """Cron-triggered violation sync (Vercel-friendly). Uses same defaults as manual sync."""
    _verify_cron_secret(x_cron_secret)
    from src.services.violation_sync_service import violation_sync_service

    # Use context manager for cron tracking to avoid connection pool exhaustion
    with get_db_session() as db:
        run = _start_cron_run(db, "violations")
        run_id = run.id

    try:
        stats = await violation_sync_service.sync_violations_smart(
            max_inspections_to_check=max_inspections,
            rate_limit_delay=1.5,
            days_back=days_back,
            min_days_between_checks=min_days_between_checks,
            max_requests=max_requests,
        )
        with get_db_session() as db:
            run = db.execute(select(CronRun).where(CronRun.id == run_id)).scalar_one()
            _finish_cron_run(db, run, "success", details=json.dumps(stats))
        return ViolationSyncResponseWithLogs(**stats)
    except Exception as exc:
        with get_db_session() as db:
            run = db.execute(select(CronRun).where(CronRun.id == run_id)).scalar_one()
            _finish_cron_run(db, run, "failed", error=str(exc))
        raise


@router.get("/cron/violations-recent", response_model=RecentViolationsSyncResponse)
async def cron_sync_recent_violations(
    inspection_days_back: int = Query(365, ge=30, le=730, description="Check inspections opened within this window"),
    max_inspections: int = Query(10, ge=1, le=500, description="Max inspections to check per run (default 10 for Vercel timeout)"),
    max_requests: int = Query(10, ge=1, le=100, description="Max API requests per run"),
    x_cron_secret: Optional[str] = Header(None),
):
    """
    Cron job to sync violations for inspections.

    Strategy: Fetches violations for inspections opened in the last N days that
    haven't been checked recently. OSHA typically issues citations ~6 months after
    inspection, so we check inspections from the past year.

    Note: DOL API does not support filtering violations by date - we must query
    by activity_nr (inspection number).
    """
    _verify_cron_secret(x_cron_secret)
    from src.services.violation_sync_service import violation_sync_service

    # Use context manager for cron tracking to avoid connection pool exhaustion
    with get_db_session() as db:
        run = _start_cron_run(db, "violations-recent")
        run_id = run.id

    try:
        stats = await violation_sync_service.sync_recent_violations(
            inspection_days_back=inspection_days_back,
            max_inspections=max_inspections,
            max_requests=max_requests,
            rate_limit_delay=1.5,
        )
        with get_db_session() as db:
            run = db.execute(select(CronRun).where(CronRun.id == run_id)).scalar_one()
            _finish_cron_run(db, run, "success", details=json.dumps(stats))
        return RecentViolationsSyncResponse(**stats)
    except Exception as exc:
        with get_db_session() as db:
            run = db.execute(select(CronRun).where(CronRun.id == run_id)).scalar_one()
            _finish_cron_run(db, run, "failed", error=str(exc))
        raise


@router.post("/sync/violations-recent", response_model=RecentViolationsSyncResponse)
async def manual_sync_recent_violations(
    inspection_days_back: int = Query(365, ge=30, le=730, description="Check inspections opened within this window"),
    max_inspections: int = Query(10, ge=1, le=500, description="Max inspections to check per run (default 10 for Vercel timeout)"),
    max_requests: int = Query(10, ge=1, le=100, description="Max API requests per run"),
    db: Session = Depends(get_db),
):
    """
    Manually trigger violations sync.

    Fetches violations for inspections opened in the last N days that haven't
    been checked recently or have no violations yet.
    """
    from src.services.violation_sync_service import violation_sync_service

    stats = await violation_sync_service.sync_recent_violations(
        inspection_days_back=inspection_days_back,
        max_inspections=max_inspections,
        max_requests=max_requests,
        rate_limit_delay=1.5,
    )
    return RecentViolationsSyncResponse(**stats)


@router.post("/sync/violations-bulk", response_model=BulkViolationsSyncResponse)
async def manual_sync_violations_bulk(
    days_back: int = Query(180, ge=30, le=365, description="How far back to fetch violations (days)"),
    max_requests: int = Query(6, ge=1, le=200, description="Max API requests per run (default 6 for Vercel timeout)"),
):
    """
    Bulk fetch violations by issuance_date and upsert to database.

    This is the efficient approach:
    1. Fetch ALL violations issued in the last N days (paginated, 200 per request)
    2. Bulk upsert to Supabase violations table
    3. Matching to inspections happens via foreign key in DB, not in Python

    Much faster than the per-inspection approach since it fetches all violations
    in one paginated sweep rather than querying by activity_nr.
    """
    from src.services.violation_sync_service import violation_sync_service

    stats = await violation_sync_service.sync_violations_bulk(
        days_back=days_back,
        max_requests=max_requests,
    )
    return BulkViolationsSyncResponse(**stats)


@router.get("/cron/violations-bulk", response_model=BulkViolationsSyncResponse)
async def cron_sync_violations_bulk(
    days_back: int = Query(180, ge=30, le=365, description="How far back to fetch violations (days)"),
    max_requests: int = Query(6, ge=1, le=200, description="Max API requests per run (default 6 for Vercel timeout)"),
    x_cron_secret: Optional[str] = Header(None),
):
    """
    Cron job for bulk violation sync by issuance_date.

    Efficient approach that fetches all recent violations in one paginated sweep,
    then upserts to the violations table. Matching to inspections happens via
    foreign key relationship in the database.
    """
    _verify_cron_secret(x_cron_secret)
    from src.services.violation_sync_service import violation_sync_service

    # Use context manager for cron tracking to avoid connection pool exhaustion
    with get_db_session() as db:
        run = _start_cron_run(db, "violations-bulk")
        run_id = run.id

    try:
        stats = await violation_sync_service.sync_violations_bulk(
            days_back=days_back,
            max_requests=max_requests,
        )
        with get_db_session() as db:
            run = db.execute(select(CronRun).where(CronRun.id == run_id)).scalar_one()
            _finish_cron_run(db, run, "success", details=json.dumps(stats))
        return BulkViolationsSyncResponse(**stats)
    except Exception as exc:
        with get_db_session() as db:
            run = db.execute(select(CronRun).where(CronRun.id == run_id)).scalar_one()
            _finish_cron_run(db, run, "failed", error=str(exc))
        raise


@router.get("/cron/status")
async def cron_status(
    request: Request,
    limit: int = Query(20, ge=1, le=100, description="Number of runs to return"),
    format: Optional[str] = Query(None, description="Response format: 'html' for web page, default is JSON"),
    x_cron_secret: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Get recent cron run status and details."""
    _verify_cron_secret(x_cron_secret)

    runs = db.execute(
        select(CronRun).order_by(CronRun.started_at.desc()).limit(limit)
    ).scalars().all()

    latest = {}
    for run in runs:
        if run.job_name not in latest:
            latest[run.job_name] = {
                "id": run.id,
                "job_name": run.job_name,
                "status": run.status,
                "started_at": _format_dt(run.started_at),
                "finished_at": _format_dt(run.finished_at),
                "details": run.details,
                "error": run.error,
            }

    # Return HTML if explicitly requested via format param, or if browser is requesting HTML
    accept = request.headers.get("accept", "")
    if format == "html" or (format is None and "text/html" in accept and "application/json" not in accept):
        return _render_cron_status_html(latest, runs)

    return {
        "latest": latest,
        "runs": [
            {
                "id": r.id,
                "job_name": r.job_name,
                "status": r.status,
                "started_at": _format_dt(r.started_at),
                "finished_at": _format_dt(r.finished_at),
                "details": r.details,
                "error": r.error,
            }
            for r in runs
        ],
    }


def _render_cron_status_html(latest: dict, runs: list) -> HTMLResponse:
    """Render cron status as a readable HTML page."""

    def format_details(details_str):
        if not details_str:
            return ""
        try:
            details = json.loads(details_str)
            parts = []
            for key, value in details.items():
                if key != "logs":
                    parts.append(f"<span class='detail'>{key}: <strong>{value}</strong></span>")
            return " | ".join(parts)
        except:
            return details_str

    def status_badge(status):
        colors = {
            "success": "bg-green-100 text-green-800",
            "failed": "bg-red-100 text-red-800",
            "running": "bg-yellow-100 text-yellow-800",
        }
        color = colors.get(status, "bg-gray-100 text-gray-800")
        return f'<span class="px-2 py-1 text-xs font-medium rounded-full {color}">{status}</span>'

    def format_time(dt_str):
        if not dt_str:
            return "—"
        return dt_str.replace("T", " ").replace("Z", " UTC")

    # Build latest section
    latest_html = ""
    job_order = ["inspections", "violations-bulk", "epa"]
    for job_name in job_order:
        if job_name in latest:
            run = latest[job_name]
            latest_html += f'''
            <div class="bg-white rounded-lg shadow p-4 mb-3">
                <div class="flex justify-between items-center mb-2">
                    <span class="font-semibold text-gray-800">{run['job_name'].replace('-', ' ').title()}</span>
                    {status_badge(run['status'])}
                </div>
                <div class="text-sm text-gray-600 space-y-1">
                    <div>Started: {format_time(run['started_at'])}</div>
                    <div>Finished: {format_time(run['finished_at'])}</div>
                    <div class="text-xs mt-2">{format_details(run['details'])}</div>
                    {f'<div class="text-red-600 text-xs mt-1">Error: {run["error"]}</div>' if run.get('error') else ''}
                </div>
            </div>
            '''

    # Build runs table
    runs_rows = ""
    for r in runs:
        runs_rows += f'''
        <tr class="border-b hover:bg-gray-50">
            <td class="px-4 py-2 text-sm">{r.id}</td>
            <td class="px-4 py-2 text-sm font-medium">{r.job_name}</td>
            <td class="px-4 py-2">{status_badge(r.status)}</td>
            <td class="px-4 py-2 text-sm text-gray-600">{format_time(_format_dt(r.started_at))}</td>
            <td class="px-4 py-2 text-sm text-gray-600">{format_time(_format_dt(r.finished_at))}</td>
            <td class="px-4 py-2 text-xs text-gray-500 max-w-md truncate">{format_details(r.details)}</td>
            <td class="px-4 py-2 text-xs text-red-600 max-w-xs truncate">{r.error or '—'}</td>
        </tr>
        '''

    html = f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Cron Status - TSG Safety Tracker</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <meta http-equiv="refresh" content="30">
    </head>
    <body class="bg-gray-100 min-h-screen">
        <nav class="bg-gray-800 text-white px-6 py-3">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-6">
                    <span class="font-semibold">TSG Safety Tracker</span>
                    <a href="/osha" class="text-sm text-gray-300 hover:text-white">OSHA</a>
                    <a href="/epa" class="text-sm text-gray-300 hover:text-white">EPA</a>
                    <a href="/crm" class="text-sm text-gray-300 hover:text-white">CRM</a>
                </div>
                <span class="text-xs text-gray-400">Auto-refreshes every 30s</span>
            </div>
        </nav>

        <main class="max-w-6xl mx-auto px-4 py-8">
            <h1 class="text-2xl font-bold text-gray-800 mb-6">Cron Sync Status</h1>

            <div class="grid md:grid-cols-3 gap-4 mb-8">
                <div class="md:col-span-3">
                    <h2 class="text-lg font-semibold text-gray-700 mb-3">Latest Runs</h2>
                </div>
                {latest_html}
            </div>

            <div>
                <h2 class="text-lg font-semibold text-gray-700 mb-3">Run History</h2>
                <div class="bg-white rounded-lg shadow overflow-x-auto">
                    <table class="w-full">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Job</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Started</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Finished</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Details</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Error</th>
                            </tr>
                        </thead>
                        <tbody>
                            {runs_rows}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="mt-8 text-center">
                <a href="/api/inspections/cron/status?format=html&limit=100" class="text-blue-600 hover:text-blue-800 text-sm">View more runs</a>
                <span class="text-gray-400 mx-2">|</span>
                <a href="/osha" class="text-blue-600 hover:text-blue-800 text-sm">Back to Dashboard</a>
            </div>
        </main>
    </body>
    </html>
    '''
    return HTMLResponse(content=html, media_type="text/html; charset=utf-8")


@router.get("/cron/stream")
async def cron_status_stream(
    request: Request,
    last_id: int = Query(0, ge=0, description="Last seen cron run id"),
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
    x_cron_secret: Optional[str] = Header(None),
):
    """Stream cron status updates when a cron job completes."""
    _verify_cron_secret(x_cron_secret)

    start_id = last_id
    if last_event_id and last_event_id.isdigit():
        start_id = max(start_id, int(last_event_id))

    async def event_generator():
        last_sent_id = start_id
        keepalive_interval = 15.0
        poll_interval = 2.0
        last_keepalive = time.monotonic()

        yield "retry: 5000\n\n"

        while True:
            if await request.is_disconnected():
                break

            with get_db_session() as db:
                run = db.execute(
                    select(CronRun)
                    .where(CronRun.finished_at.isnot(None))
                    .where(CronRun.id > last_sent_id)
                    .order_by(CronRun.id.desc())
                    .limit(1)
                ).scalar_one_or_none()

                if run:
                    last_sent_id = run.id
                    runs = db.execute(
                        select(CronRun).order_by(CronRun.started_at.desc()).limit(20)
                    ).scalars().all()

                    latest = {}
                    for entry in runs:
                        if entry.job_name not in latest:
                            latest[entry.job_name] = {
                                "id": entry.id,
                                "job_name": entry.job_name,
                                "status": entry.status,
                                "started_at": _format_dt(entry.started_at),
                                "finished_at": _format_dt(entry.finished_at),
                                "details": entry.details,
                                "error": entry.error,
                            }

                    payload = json.dumps({
                        "latest": latest,
                        "run_id": last_sent_id,
                    })
                    yield f"id: {last_sent_id}\nevent: cron_update\ndata: {payload}\n\n"
                    last_keepalive = time.monotonic()
                elif time.monotonic() - last_keepalive >= keepalive_interval:
                    yield ": keepalive\n\n"
                    last_keepalive = time.monotonic()

            await asyncio.sleep(poll_interval)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/{inspection_id}/sync-violations")
async def sync_violations_for_inspection(inspection_id: int, db: Session = Depends(get_db)):
    """Sync violations for a specific inspection (on-demand)."""
    from src.services.violation_sync_service import violation_sync_service

    # Get inspection
    inspection = db.execute(
        select(Inspection).where(Inspection.id == inspection_id)
    ).scalar_one_or_none()

    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    stats = await violation_sync_service.sync_violations_for_inspection(
        inspection.activity_nr
    )

    return {
        "success": True,
        "activity_nr": inspection.activity_nr,
        **stats
    }


class EnrichmentResponse(BaseModel):
    """Response model for enrichment operation."""
    success: bool
    website_url: Optional[str]
    data: Optional[dict]
    error: Optional[str]
    confidence: Optional[str] = None  # high, medium, low, or none


class ContactResponse(BaseModel):
    """Response model for contact data."""
    id: int
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: Optional[str]
    title: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    linkedin_url: Optional[str]
    contact_type: Optional[str]

    class Config:
        from_attributes = True


class CompanyDataResponse(BaseModel):
    """Response model for company data."""
    id: int
    inspection_id: Optional[int] = None
    name: str
    domain: Optional[str]
    website: Optional[str]
    description: Optional[str]
    industry: Optional[str]
    sub_industry: Optional[str]
    employee_count: Optional[int]
    employee_range: Optional[str]
    year_founded: Optional[int]
    business_type: Optional[str]
    registration_state: Optional[str]
    registration_number: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    postal_code: Optional[str]
    linkedin_url: Optional[str]
    facebook_url: Optional[str]
    twitter_url: Optional[str]
    instagram_url: Optional[str]
    youtube_url: Optional[str]
    other_addresses: Optional[str]  # JSON string
    services: Optional[str]  # JSON string
    confidence: Optional[str] = None  # high, medium, low - data verification confidence
    contacted: bool = False
    contacted_date: Optional[str] = None
    contact_notes: Optional[str] = None
    created_at: Optional[str] = None
    contacts: List[ContactResponse] = []

    class Config:
        from_attributes = True


class EnrichedCompanyListItem(BaseModel):
    """Summary item for enriched companies list."""
    id: int
    inspection_id: int
    name: str
    industry: Optional[str]
    city: Optional[str]
    state: Optional[str]
    phone: Optional[str]
    website: Optional[str]
    contacted: bool = False
    contacted_date: Optional[str] = None
    created_at: Optional[str] = None
    # Include inspection info
    inspection_estab_name: Optional[str] = None
    inspection_open_date: Optional[str] = None
    total_penalty: Optional[float] = None

    class Config:
        from_attributes = True


class EnrichedCompaniesResponse(BaseModel):
    """Response for enriched companies list."""
    items: List[EnrichedCompanyListItem]
    total: int


@router.post("/{inspection_id}/enrich", response_model=EnrichmentResponse)
async def enrich_inspection(inspection_id: int, db: Session = Depends(get_db)):
    """Enrich inspection with company data from multiple web sources."""
    from datetime import datetime
    import json

    # Get the inspection
    inspection = db.execute(
        select(Inspection).where(Inspection.id == inspection_id)
    ).scalar_one_or_none()

    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    # Update enrichment status
    inspection.enrichment_status = EnrichmentStatus.IN_PROGRESS
    inspection.enrichment_attempts = (inspection.enrichment_attempts or 0) + 1
    inspection.last_enrichment_attempt = datetime.utcnow()
    db.commit()

    try:
        # Run enrichment
        result = await web_enrichment_service.enrich_company(
            company_name=inspection.estab_name,
            city=inspection.site_city,
            state=inspection.site_state
        )

        if result["success"] and result["data"]:
            data = result["data"]

            # Check if company already exists
            existing_company = db.execute(
                select(Company).where(Company.inspection_id == inspection_id)
            ).scalar_one_or_none()

            # Extract domain from website URL
            domain = None
            if result.get("website_url"):
                domain = result["website_url"].replace("https://", "").replace("http://", "").split("/")[0]

            # Parse employee count
            employee_count = None
            employee_range = data.get("employee_range")
            if data.get("employee_count"):
                try:
                    employee_count = int(data["employee_count"])
                except (ValueError, TypeError):
                    pass

            # Get headquarters info
            hq = data.get("headquarters") or {}
            contact_info = data.get("contact_info") or {}
            social = data.get("social_media") or {}
            registration = data.get("business_registration") or {}

            # Serialize other_locations and services as JSON
            other_locations_json = None
            if data.get("other_locations"):
                other_locations_json = json.dumps(data["other_locations"])

            services_json = None
            if data.get("services"):
                services_json = json.dumps(data["services"])

            if existing_company:
                # Update existing company
                existing_company.name = data.get("official_name") or inspection.estab_name
                existing_company.domain = domain
                existing_company.website = result.get("website_url")
                existing_company.industry = data.get("industry")
                existing_company.sub_industry = data.get("sub_industry")
                existing_company.description = data.get("description")
                existing_company.services = services_json
                existing_company.employee_count = employee_count
                existing_company.employee_range = employee_range

                # Contact info
                existing_company.phone = contact_info.get("main_phone")
                existing_company.email = contact_info.get("main_email")

                # Social media
                existing_company.linkedin_url = social.get("linkedin_url")
                existing_company.facebook_url = social.get("facebook_url")
                existing_company.twitter_url = social.get("twitter_url")
                existing_company.instagram_url = social.get("instagram_url")
                existing_company.youtube_url = social.get("youtube_url")

                # Business registration
                existing_company.year_founded = data.get("year_founded")
                existing_company.registration_state = registration.get("state")
                existing_company.registration_number = registration.get("registration_number")
                existing_company.registered_agent = registration.get("registered_agent")
                existing_company.business_type = registration.get("business_type")

                # Address
                existing_company.address = hq.get("address")
                existing_company.city = hq.get("city")
                existing_company.state = hq.get("state")
                existing_company.postal_code = hq.get("postal_code")
                existing_company.other_addresses = other_locations_json

                # Data quality
                existing_company.confidence = result.get("confidence", "unknown")

                company = existing_company
            else:
                # Create new company record
                company = Company(
                    inspection_id=inspection_id,
                    name=data.get("official_name") or inspection.estab_name,
                    domain=domain,
                    website=result.get("website_url"),
                    industry=data.get("industry"),
                    sub_industry=data.get("sub_industry"),
                    description=data.get("description"),
                    services=services_json,
                    employee_count=employee_count,
                    employee_range=employee_range,
                    phone=contact_info.get("main_phone"),
                    email=contact_info.get("main_email"),
                    linkedin_url=social.get("linkedin_url"),
                    facebook_url=social.get("facebook_url"),
                    twitter_url=social.get("twitter_url"),
                    instagram_url=social.get("instagram_url"),
                    youtube_url=social.get("youtube_url"),
                    year_founded=data.get("year_founded"),
                    registration_state=registration.get("state"),
                    registration_number=registration.get("registration_number"),
                    registered_agent=registration.get("registered_agent"),
                    business_type=registration.get("business_type"),
                    address=hq.get("address"),
                    city=hq.get("city"),
                    state=hq.get("state"),
                    postal_code=hq.get("postal_code"),
                    other_addresses=other_locations_json,
                    confidence=result.get("confidence", "unknown"),
                )
                db.add(company)
                db.flush()  # Get company ID

            # Save key personnel as contacts
            if data.get("key_personnel"):
                # Delete existing contacts for this company
                db.execute(
                    Contact.__table__.delete().where(Contact.company_id == company.id)
                )

                for person in data["key_personnel"]:
                    if person.get("name"):
                        # Split name into first/last
                        name_parts = person["name"].strip().split(" ", 1)
                        first_name = name_parts[0] if name_parts else None
                        last_name = name_parts[1] if len(name_parts) > 1 else None

                        contact = Contact(
                            company_id=company.id,
                            first_name=first_name,
                            last_name=last_name,
                            full_name=person.get("name"),
                            title=person.get("title"),
                            email=person.get("email"),
                            phone=person.get("phone"),
                            linkedin_url=person.get("linkedin_url"),
                            contact_type="executive" if any(t in (person.get("title") or "").lower()
                                for t in ["owner", "ceo", "president", "vp", "director", "manager"])
                                else "other"
                        )
                        db.add(contact)

            inspection.enrichment_status = EnrichmentStatus.COMPLETED
            inspection.enrichment_error = None
            db.commit()

            return EnrichmentResponse(
                success=True,
                website_url=result.get("website_url"),
                data=result.get("data"),
                error=None,
                confidence=result.get("confidence", "unknown")
            )
        else:
            inspection.enrichment_status = EnrichmentStatus.FAILED
            inspection.enrichment_error = result.get("error", "Unknown error")
            db.commit()

            return EnrichmentResponse(
                success=False,
                website_url=result.get("website_url"),
                data=None,
                error=result.get("error"),
                confidence=result.get("confidence", "none")
            )

    except Exception as e:
        inspection.enrichment_status = EnrichmentStatus.FAILED
        inspection.enrichment_error = str(e)
        db.commit()

        return EnrichmentResponse(
            success=False,
            website_url=None,
            data=None,
            error=str(e)
        )


@router.get("/{inspection_id}/company", response_model=Optional[CompanyDataResponse])
async def get_inspection_company(inspection_id: int, db: Session = Depends(get_db)):
    """Get company data for an inspection including contacts."""
    company = db.execute(
        select(Company).where(Company.inspection_id == inspection_id)
    ).scalar_one_or_none()

    if not company:
        return None

    # Get contacts for this company
    contacts = db.execute(
        select(Contact).where(Contact.company_id == company.id)
    ).scalars().all()

    # Build response with contacts
    return CompanyDataResponse(
        id=company.id,
        name=company.name,
        domain=company.domain,
        website=company.website,
        description=company.description,
        industry=company.industry,
        sub_industry=company.sub_industry,
        employee_count=company.employee_count,
        employee_range=company.employee_range,
        year_founded=company.year_founded,
        business_type=company.business_type,
        registration_state=company.registration_state,
        registration_number=company.registration_number,
        phone=company.phone,
        email=company.email,
        address=company.address,
        city=company.city,
        state=company.state,
        postal_code=company.postal_code,
        linkedin_url=company.linkedin_url,
        facebook_url=company.facebook_url,
        twitter_url=company.twitter_url,
        instagram_url=company.instagram_url,
        youtube_url=company.youtube_url,
        other_addresses=company.other_addresses,
        services=company.services,
        confidence=company.confidence,
        contacted=company.contacted or False,
        contacted_date=company.contacted_date.isoformat() if company.contacted_date else None,
        contact_notes=company.contact_notes,
        created_at=company.created_at.isoformat() if company.created_at else None,
        contacts=[ContactResponse.model_validate(c) for c in contacts]
    )


class RelatedCompanyResponse(BaseModel):
    """Response for company data found via related inspection."""
    company: CompanyDataResponse
    source_inspection_id: int  # The inspection that has the company data
    is_direct: bool  # True if company is directly linked to the requested inspection


@router.get("/{inspection_id}/company-or-related", response_model=Optional[RelatedCompanyResponse])
async def get_inspection_company_or_related(inspection_id: int, db: Session = Depends(get_db)):
    """
    Get company data for an inspection, checking related inspections if not directly linked.
    This allows viewing enrichment data for any inspection of the same company.
    """
    # First, check if this inspection has directly linked company data
    company = db.execute(
        select(Company).where(Company.inspection_id == inspection_id)
    ).scalar_one_or_none()

    if company:
        # Get contacts for this company
        contacts = db.execute(
            select(Contact).where(Contact.company_id == company.id)
        ).scalars().all()

        return RelatedCompanyResponse(
            company=CompanyDataResponse(
                id=company.id,
                inspection_id=company.inspection_id,
                name=company.name,
                domain=company.domain,
                website=company.website,
                description=company.description,
                industry=company.industry,
                sub_industry=company.sub_industry,
                employee_count=company.employee_count,
                employee_range=company.employee_range,
                year_founded=company.year_founded,
                business_type=company.business_type,
                registration_state=company.registration_state,
                registration_number=company.registration_number,
                phone=company.phone,
                email=company.email,
                address=company.address,
                city=company.city,
                state=company.state,
                postal_code=company.postal_code,
                linkedin_url=company.linkedin_url,
                facebook_url=company.facebook_url,
                twitter_url=company.twitter_url,
                instagram_url=company.instagram_url,
                youtube_url=company.youtube_url,
                other_addresses=company.other_addresses,
                services=company.services,
                confidence=company.confidence,
                contacted=company.contacted or False,
                contacted_date=company.contacted_date.isoformat() if company.contacted_date else None,
                contact_notes=company.contact_notes,
                created_at=company.created_at.isoformat() if company.created_at else None,
                contacts=[ContactResponse.model_validate(c) for c in contacts]
            ),
            source_inspection_id=inspection_id,
            is_direct=True
        )

    # No direct company - look for related inspections with the same establishment name
    inspection = db.execute(
        select(Inspection).where(Inspection.id == inspection_id)
    ).scalar_one_or_none()

    if not inspection:
        return None

    # Find inspections with the same establishment name (case-insensitive)
    related_inspections = db.execute(
        select(Inspection).where(
            func.lower(Inspection.estab_name) == func.lower(inspection.estab_name)
        )
    ).scalars().all()

    # Check if any related inspection has company data
    for related in related_inspections:
        if related.id == inspection_id:
            continue  # Skip self

        related_company = db.execute(
            select(Company).where(Company.inspection_id == related.id)
        ).scalar_one_or_none()

        if related_company:
            # Found company data from a related inspection
            contacts = db.execute(
                select(Contact).where(Contact.company_id == related_company.id)
            ).scalars().all()

            return RelatedCompanyResponse(
                company=CompanyDataResponse(
                    id=related_company.id,
                    inspection_id=related_company.inspection_id,
                    name=related_company.name,
                    domain=related_company.domain,
                    website=related_company.website,
                    description=related_company.description,
                    industry=related_company.industry,
                    sub_industry=related_company.sub_industry,
                    employee_count=related_company.employee_count,
                    employee_range=related_company.employee_range,
                    year_founded=related_company.year_founded,
                    business_type=related_company.business_type,
                    registration_state=related_company.registration_state,
                    registration_number=related_company.registration_number,
                    phone=related_company.phone,
                    email=related_company.email,
                    address=related_company.address,
                    city=related_company.city,
                    state=related_company.state,
                    postal_code=related_company.postal_code,
                    linkedin_url=related_company.linkedin_url,
                    facebook_url=related_company.facebook_url,
                    twitter_url=related_company.twitter_url,
                    instagram_url=related_company.instagram_url,
                    youtube_url=related_company.youtube_url,
                    other_addresses=related_company.other_addresses,
                    services=related_company.services,
                    confidence=related_company.confidence,
                    contacted=related_company.contacted or False,
                    contacted_date=related_company.contacted_date.isoformat() if related_company.contacted_date else None,
                    contact_notes=related_company.contact_notes,
                    created_at=related_company.created_at.isoformat() if related_company.created_at else None,
                    contacts=[ContactResponse.model_validate(c) for c in contacts]
                ),
                source_inspection_id=related.id,
                is_direct=False
            )

    return None


@router.get("/companies/enriched", response_model=EnrichedCompaniesResponse)
async def get_enriched_companies(
    contacted_filter: Optional[str] = Query(None, description="Filter: 'contacted', 'not_contacted', or None for all"),
    exclude_in_crm: bool = Query(True, description="Exclude companies already added to CRM"),
    db: Session = Depends(get_db)
):
    """Get all enriched companies with their inspection info."""
    from sqlalchemy.orm import joinedload
    from src.database.models import Prospect

    query = select(Company).options(joinedload(Company.inspection))

    # Apply contacted filter
    if contacted_filter == "contacted":
        query = query.where(Company.contacted == True)
    elif contacted_filter == "not_contacted":
        query = query.where((Company.contacted == False) | (Company.contacted == None))

    # Exclude companies whose inspections are already in the CRM (have prospects)
    if exclude_in_crm:
        prospect_inspection_ids = select(Prospect.inspection_id)
        query = query.where(~Company.inspection_id.in_(prospect_inspection_ids))

    # Order by most recent first
    query = query.order_by(desc(Company.created_at))

    companies = db.execute(query).scalars().unique().all()

    items = []
    for company in companies:
        inspection = company.inspection
        items.append(EnrichedCompanyListItem(
            id=company.id,
            inspection_id=company.inspection_id,
            name=company.name,
            industry=company.industry,
            city=company.city,
            state=company.state,
            phone=company.phone,
            website=company.website,
            contacted=company.contacted or False,
            contacted_date=company.contacted_date.isoformat() if company.contacted_date else None,
            created_at=company.created_at.isoformat() if company.created_at else None,
            inspection_estab_name=inspection.estab_name if inspection else None,
            inspection_open_date=inspection.open_date.isoformat() if inspection and inspection.open_date else None,
            total_penalty=float(inspection.total_current_penalty) if inspection and inspection.total_current_penalty else None
        ))

    return EnrichedCompaniesResponse(items=items, total=len(items))


@router.get("/companies/{company_id}", response_model=CompanyDataResponse)
async def get_company_by_id(company_id: int, db: Session = Depends(get_db)):
    """Get company data by company ID."""
    company = db.execute(
        select(Company).where(Company.id == company_id)
    ).scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Get contacts for this company
    contacts = db.execute(
        select(Contact).where(Contact.company_id == company.id)
    ).scalars().all()

    return CompanyDataResponse(
        id=company.id,
        inspection_id=company.inspection_id,
        name=company.name,
        domain=company.domain,
        website=company.website,
        description=company.description,
        industry=company.industry,
        sub_industry=company.sub_industry,
        employee_count=company.employee_count,
        employee_range=company.employee_range,
        year_founded=company.year_founded,
        business_type=company.business_type,
        registration_state=company.registration_state,
        registration_number=company.registration_number,
        phone=company.phone,
        email=company.email,
        address=company.address,
        city=company.city,
        state=company.state,
        postal_code=company.postal_code,
        linkedin_url=company.linkedin_url,
        facebook_url=company.facebook_url,
        twitter_url=company.twitter_url,
        instagram_url=company.instagram_url,
        youtube_url=company.youtube_url,
        other_addresses=company.other_addresses,
        services=company.services,
        confidence=company.confidence,
        contacted=company.contacted or False,
        contacted_date=company.contacted_date.isoformat() if company.contacted_date else None,
        contact_notes=company.contact_notes,
        created_at=company.created_at.isoformat() if company.created_at else None,
        contacts=[ContactResponse.model_validate(c) for c in contacts]
    )


class CompanyUpdateRequest(BaseModel):
    """Request to update company data."""
    name: Optional[str] = None
    domain: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    sub_industry: Optional[str] = None
    employee_count: Optional[int] = None
    employee_range: Optional[str] = None
    year_founded: Optional[int] = None
    business_type: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    linkedin_url: Optional[str] = None
    facebook_url: Optional[str] = None
    twitter_url: Optional[str] = None
    instagram_url: Optional[str] = None
    youtube_url: Optional[str] = None


class ContactedUpdateRequest(BaseModel):
    """Request to update contacted status."""
    contacted: bool
    notes: Optional[str] = None


@router.patch("/companies/{company_id}")
async def update_company(
    company_id: int,
    request: CompanyUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update company data fields."""
    from datetime import datetime

    company = db.execute(
        select(Company).where(Company.id == company_id)
    ).scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Update only the fields that were provided
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(company, field):
            setattr(company, field, value)

    company.updated_at = datetime.utcnow()
    db.commit()

    return {
        "success": True,
        "id": company.id,
        "name": company.name,
        "updated_fields": list(update_data.keys())
    }


@router.patch("/companies/{company_id}/contacted")
async def update_company_contacted(
    company_id: int,
    request: ContactedUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update the contacted status of a company."""
    from datetime import datetime

    company = db.execute(
        select(Company).where(Company.id == company_id)
    ).scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    company.contacted = request.contacted
    if request.contacted:
        company.contacted_date = datetime.utcnow()
    else:
        company.contacted_date = None

    if request.notes is not None:
        company.contact_notes = request.notes

    db.commit()

    return {
        "success": True,
        "contacted": company.contacted,
        "contacted_date": company.contacted_date.isoformat() if company.contacted_date else None,
        "contact_notes": company.contact_notes
    }


class RelatedInspectionItem(BaseModel):
    """Related inspection summary."""
    id: int
    activity_nr: str
    estab_name: str
    site_city: Optional[str] = None
    site_state: Optional[str] = None
    open_date: Optional[str] = None
    close_case_date: Optional[str] = None
    total_current_penalty: Optional[float] = None
    violation_count: int = 0
    is_primary: bool = False  # True if this is the inspection linked to the company


class RelatedInspectionsResponse(BaseModel):
    """Response for related inspections."""
    company_id: int
    company_name: str
    inspections: list[RelatedInspectionItem]
    total: int


@router.get("/companies/{company_id}/related-inspections", response_model=RelatedInspectionsResponse)
async def get_related_inspections(company_id: int, db: Session = Depends(get_db)):
    """
    Get all inspections related to a company.
    Finds inspections with matching or similar establishment names.
    Always includes the primary inspection linked to the company.
    """
    # Get the company
    company = db.execute(
        select(Company).where(Company.id == company_id)
    ).scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Get the primary inspection linked to this company
    primary_inspection = db.execute(
        select(Inspection).where(Inspection.id == company.inspection_id)
    ).scalar_one_or_none()

    if not primary_inspection:
        return RelatedInspectionsResponse(
            company_id=company.id,
            company_name=company.name,
            inspections=[],
            total=0
        )

    # Get the establishment name for matching
    estab_name = primary_inspection.estab_name

    # Build name conditions for matching related inspections
    # Always include the primary inspection by ID, plus match on names
    name_conditions = [
        Inspection.id == company.inspection_id,  # Always include primary
        func.lower(Inspection.estab_name) == func.lower(estab_name)
    ]

    if company.name and company.name.lower() != estab_name.lower():
        name_conditions.append(func.lower(Inspection.estab_name) == func.lower(company.name))

    if company.legal_name:
        name_conditions.append(func.lower(Inspection.estab_name) == func.lower(company.legal_name))

    if company.operating_name:
        name_conditions.append(func.lower(Inspection.estab_name) == func.lower(company.operating_name))

    # Build final query with OR conditions
    query = select(Inspection).where(or_(*name_conditions)).order_by(desc(Inspection.open_date))

    inspections = db.execute(query).scalars().all()

    # Get violation counts for each inspection
    items = []
    for insp in inspections:
        violation_count = db.execute(
            select(func.count(Violation.id)).where(Violation.activity_nr == insp.activity_nr)
        ).scalar() or 0

        items.append(RelatedInspectionItem(
            id=insp.id,
            activity_nr=insp.activity_nr,
            estab_name=insp.estab_name,
            site_city=insp.site_city,
            site_state=insp.site_state,
            open_date=insp.open_date.isoformat() if insp.open_date else None,
            close_case_date=insp.close_case_date.isoformat() if insp.close_case_date else None,
            total_current_penalty=float(insp.total_current_penalty) if insp.total_current_penalty else None,
            violation_count=violation_count,
            is_primary=(insp.id == company.inspection_id)
        ))

    return RelatedInspectionsResponse(
        company_id=company.id,
        company_name=company.name,
        inspections=items,
        total=len(items)
    )
