"""EPA enforcement cases API endpoints."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Query, HTTPException, BackgroundTasks, Header
from pydantic import BaseModel
from sqlalchemy import func, desc, asc, select

from src.database.connection import get_db_session
from src.database.models import EPACase, CronRun
from src.services.epa_sync_service import epa_sync_service
from src.config import settings
import json

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class EPACaseResponse(BaseModel):
    id: int
    case_number: str
    activity_id: Optional[str] = None
    case_name: Optional[str] = None
    case_category: Optional[str] = None
    case_category_desc: Optional[str] = None
    case_status: Optional[str] = None
    case_status_desc: Optional[str] = None
    civil_criminal: Optional[str] = None
    case_lead: Optional[str] = None
    region: Optional[str] = None
    date_filed: Optional[str] = None
    settlement_date: Optional[str] = None
    date_closed: Optional[str] = None
    fed_penalty: float = 0
    state_local_penalty: float = 0
    total_penalty: float = 0
    facility_name: Optional[str] = None
    facility_city: Optional[str] = None
    facility_state: Optional[str] = None
    primary_law: Optional[str] = None
    laws_violated: List[str] = []
    created_at: Optional[str] = None
    echo_url: Optional[str] = None  # Link to EPA ECHO case detail page

    class Config:
        from_attributes = True


class EPAStatsResponse(BaseModel):
    total_cases: int
    total_penalties: float
    states_count: int
    avg_penalty: float
    by_law: dict
    by_status: dict
    recent_cases: int


class EPAListResponse(BaseModel):
    items: List[EPACaseResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SyncResponse(BaseModel):
    success: bool
    message: str
    stats: Optional[dict] = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def case_to_response(case: EPACase) -> EPACaseResponse:
    """Convert EPACase model to response."""
    laws_violated = []
    if case.caa_flag:
        laws_violated.append("CAA")
    if case.cwa_flag:
        laws_violated.append("CWA")
    if case.rcra_flag:
        laws_violated.append("RCRA")
    if case.sdwa_flag:
        laws_violated.append("SDWA")
    if case.cercla_flag:
        laws_violated.append("CERCLA")
    if case.epcra_flag:
        laws_violated.append("EPCRA")
    if case.tsca_flag:
        laws_violated.append("TSCA")
    if case.fifra_flag:
        laws_violated.append("FIFRA")

    # Generate EPA ECHO URL - use case number for enforcement case report
    echo_url = None
    if case.case_number:
        # URL encode the case number (replace spaces, special chars)
        encoded_case = case.case_number.replace(" ", "%20")
        echo_url = f"https://echo.epa.gov/enforcement-case-report?id={encoded_case}"

    return EPACaseResponse(
        id=case.id,
        case_number=case.case_number,
        activity_id=case.activity_id,
        case_name=case.case_name,
        case_category=case.case_category,
        case_category_desc=case.case_category_desc,
        case_status=case.case_status,
        case_status_desc=case.case_status_desc,
        civil_criminal=case.civil_criminal,
        case_lead=case.case_lead,
        region=case.region,
        date_filed=case.date_filed.isoformat() if case.date_filed else None,
        settlement_date=case.settlement_date.isoformat() if case.settlement_date else None,
        date_closed=case.date_closed.isoformat() if case.date_closed else None,
        fed_penalty=case.fed_penalty or 0,
        state_local_penalty=case.state_local_penalty or 0,
        total_penalty=(case.fed_penalty or 0) + (case.state_local_penalty or 0),
        facility_name=case.facility_name,
        facility_city=case.facility_city,
        facility_state=case.facility_state,
        primary_law=case.primary_law,
        laws_violated=laws_violated,
        created_at=case.created_at.isoformat() if case.created_at else None,
        echo_url=echo_url
    )


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/list", response_model=EPAListResponse)
async def list_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    state: Optional[str] = None,
    law: Optional[str] = None,
    case_status: Optional[str] = None,
    min_penalty: Optional[float] = None,
    max_penalty: Optional[float] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_by: str = Query("settlement_date", pattern="^(date_filed|settlement_date|date_closed|case_name|fed_penalty|facility_state)$"),
    sort_desc: bool = True
):
    """List EPA enforcement cases with filtering and pagination.

    Sort options: settlement_date (default), date_filed, date_closed, case_name, fed_penalty, facility_state
    """
    with get_db_session() as db:
        query = db.query(EPACase)

        # Apply filters
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (EPACase.case_name.ilike(search_pattern)) |
                (EPACase.facility_name.ilike(search_pattern)) |
                (EPACase.case_number.ilike(search_pattern))
            )

        if state:
            query = query.filter(EPACase.facility_state == state.upper())

        if law:
            law_upper = law.upper()
            if law_upper == "CAA":
                query = query.filter(EPACase.caa_flag == True)
            elif law_upper == "CWA":
                query = query.filter(EPACase.cwa_flag == True)
            elif law_upper == "RCRA":
                query = query.filter(EPACase.rcra_flag == True)
            elif law_upper == "SDWA":
                query = query.filter(EPACase.sdwa_flag == True)
            elif law_upper == "CERCLA":
                query = query.filter(EPACase.cercla_flag == True)
            elif law_upper == "EPCRA":
                query = query.filter(EPACase.epcra_flag == True)
            elif law_upper == "TSCA":
                query = query.filter(EPACase.tsca_flag == True)
            elif law_upper == "FIFRA":
                query = query.filter(EPACase.fifra_flag == True)

        if case_status:
            query = query.filter(EPACase.case_status == case_status)

        if min_penalty is not None:
            query = query.filter(EPACase.fed_penalty >= min_penalty)

        if max_penalty is not None:
            query = query.filter(EPACase.fed_penalty <= max_penalty)

        if start_date:
            query = query.filter(EPACase.date_filed >= start_date)

        if end_date:
            query = query.filter(EPACase.date_filed <= end_date)

        # Get total count
        total = query.count()

        # Apply sorting
        sort_column = getattr(EPACase, sort_by, EPACase.date_filed)
        if sort_desc:
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # Apply pagination
        offset = (page - 1) * page_size
        cases = query.offset(offset).limit(page_size).all()

        return EPAListResponse(
            items=[case_to_response(c) for c in cases],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )


@router.get("/stats", response_model=EPAStatsResponse)
async def get_stats(
    state: Optional[str] = None,
    law: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get EPA enforcement statistics."""
    with get_db_session() as db:
        filters = []
        if state:
            filters.append(EPACase.facility_state == state.upper())
        if start_date:
            filters.append(EPACase.date_filed >= start_date)
        if end_date:
            filters.append(EPACase.date_filed <= end_date)

        stats_query = select(
            func.count(EPACase.id),
            func.coalesce(func.sum(EPACase.fed_penalty), 0),
            func.count(func.distinct(EPACase.facility_state)),
            func.count(EPACase.id).filter(EPACase.caa_flag == True),
            func.count(EPACase.id).filter(EPACase.cwa_flag == True),
            func.count(EPACase.id).filter(EPACase.rcra_flag == True),
            func.count(EPACase.id).filter(EPACase.sdwa_flag == True),
            func.count(EPACase.id).filter(EPACase.cercla_flag == True),
            func.count(EPACase.id).filter(EPACase.epcra_flag == True),
            func.count(EPACase.id).filter(EPACase.tsca_flag == True),
            func.count(EPACase.id).filter(EPACase.fifra_flag == True),
        )
        if filters:
            stats_query = stats_query.where(*filters)

        result = db.execute(stats_query).one()
        total_cases = result[0] or 0
        total_penalties = result[1] or 0
        states_count = result[2] or 0

        # Average penalty
        avg_penalty = total_penalties / total_cases if total_cases > 0 else 0

        # Cases by law
        by_law = {
            "CAA": result[3] or 0,
            "CWA": result[4] or 0,
            "RCRA": result[5] or 0,
            "SDWA": result[6] or 0,
            "CERCLA": result[7] or 0,
            "EPCRA": result[8] or 0,
            "TSCA": result[9] or 0,
            "FIFRA": result[10] or 0,
        }

        # Cases by status
        status_query = select(
            EPACase.case_status,
            func.count(EPACase.id)
        ).group_by(EPACase.case_status)
        if filters:
            status_query = status_query.where(*filters)
        status_counts = db.execute(status_query).all()
        by_status = {s[0] or "Unknown": s[1] for s in status_counts}

        # Recent cases (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_query = select(func.count(EPACase.id)).where(
            EPACase.date_filed >= thirty_days_ago.date()
        )
        if filters:
            recent_query = recent_query.where(*filters)
        recent_cases = db.execute(recent_query).scalar() or 0

        return EPAStatsResponse(
            total_cases=total_cases,
            total_penalties=total_penalties,
            states_count=states_count,
            avg_penalty=avg_penalty,
            by_law=by_law,
            by_status=by_status,
            recent_cases=recent_cases
        )


@router.get("/states")
async def get_states():
    """Get list of states with case counts."""
    with get_db_session() as db:
        results = db.query(
            EPACase.facility_state,
            func.count(EPACase.id)
        ).filter(
            EPACase.facility_state.isnot(None)
        ).group_by(
            EPACase.facility_state
        ).order_by(
            EPACase.facility_state
        ).all()

        return [{"state": r[0], "count": r[1]} for r in results]


@router.get("/laws")
async def get_laws():
    """Get list of environmental laws with case counts."""
    with get_db_session() as db:
        return [
            {"law": "CAA", "name": "Clean Air Act", "count": db.query(EPACase).filter(EPACase.caa_flag == True).count()},
            {"law": "CWA", "name": "Clean Water Act", "count": db.query(EPACase).filter(EPACase.cwa_flag == True).count()},
            {"law": "RCRA", "name": "Resource Conservation and Recovery Act", "count": db.query(EPACase).filter(EPACase.rcra_flag == True).count()},
            {"law": "SDWA", "name": "Safe Drinking Water Act", "count": db.query(EPACase).filter(EPACase.sdwa_flag == True).count()},
            {"law": "CERCLA", "name": "Superfund", "count": db.query(EPACase).filter(EPACase.cercla_flag == True).count()},
            {"law": "EPCRA", "name": "Emergency Planning and Community Right-to-Know Act", "count": db.query(EPACase).filter(EPACase.epcra_flag == True).count()},
            {"law": "TSCA", "name": "Toxic Substances Control Act", "count": db.query(EPACase).filter(EPACase.tsca_flag == True).count()},
            {"law": "FIFRA", "name": "Federal Insecticide, Fungicide, and Rodenticide Act", "count": db.query(EPACase).filter(EPACase.fifra_flag == True).count()},
        ]


@router.get("/sync/test")
async def sync_test():
    """Test endpoint to verify the sync route is reachable."""
    return {"status": "ok", "message": "EPA sync route is reachable", "method": "GET"}


@router.post("/sync/test")
async def sync_test_post():
    """Test endpoint to verify POST to sync route works."""
    return {"status": "ok", "message": "EPA sync POST route is reachable", "method": "POST"}


@router.post("/sync", response_model=SyncResponse)
async def sync_cases(
    background_tasks: BackgroundTasks,
    states: Optional[str] = Query(None, description="Comma-separated state codes"),
    days_back: int = Query(90, ge=1, le=365),
    min_penalty: float = Query(0, ge=0)
):
    """Trigger EPA case sync from ECHO API."""
    state_list = [s.strip().upper() for s in states.split(",")] if states else None

    with get_db_session() as db:
        run = CronRun(job_name="epa", status="running")
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id

    def run_sync(run_id_value: int):
        # Run the async bulk sync operation (single db session)
        try:
            stats = asyncio.run(epa_sync_service.sync_cases_bulk(
                states=state_list,
                days_back=days_back,
                min_penalty=min_penalty
            ))
            # Update cron run status in separate session after sync completes
            with get_db_session() as db:
                run_row = db.query(CronRun).filter(CronRun.id == run_id_value).first()
                if run_row:
                    run_row.status = "success"
                    run_row.finished_at = datetime.utcnow()
                    run_row.details = json.dumps(stats)
                    db.commit()
            logger.info(f"EPA sync completed: {stats}")
        except Exception as e:
            logger.error(f"EPA sync error: {e}")
            with get_db_session() as db:
                run_row = db.query(CronRun).filter(CronRun.id == run_id_value).first()
                if run_row:
                    run_row.status = "failed"
                    run_row.finished_at = datetime.utcnow()
                    run_row.error = str(e)
                    db.commit()

    background_tasks.add_task(run_sync, run_id)

    return SyncResponse(
        success=True,
        message=f"EPA sync started for {'all states' if not state_list else ', '.join(state_list)} ({days_back} days back)",
        stats={"run_id": run_id},
    )


@router.get("/sync/status")
async def sync_status():
    """Get latest EPA sync run status."""
    with get_db_session() as db:
        run = db.query(CronRun).filter(CronRun.job_name == "epa").order_by(CronRun.started_at.desc()).first()
        if not run:
            return {"latest": None}
        return {
            "latest": {
                "id": run.id,
                "status": run.status,
                "started_at": run.started_at.isoformat() + "Z" if run.started_at else None,
                "finished_at": run.finished_at.isoformat() + "Z" if run.finished_at else None,
                "details": run.details,
                "error": run.error,
            }
        }


@router.get("/sync/history")
async def sync_history(limit: int = Query(10, ge=1, le=50)):
    """Get EPA sync run history with errors."""
    with get_db_session() as db:
        runs = db.query(CronRun).filter(CronRun.job_name == "epa").order_by(CronRun.started_at.desc()).limit(limit).all()
        return {
            "runs": [
                {
                    "id": run.id,
                    "status": run.status,
                    "started_at": run.started_at.isoformat() + "Z" if run.started_at else None,
                    "finished_at": run.finished_at.isoformat() + "Z" if run.finished_at else None,
                    "details": run.details,
                    "error": run.error,
                }
                for run in runs
            ]
        }


# Target states for EPA sync (same as OSHA sync - Southeast + Texas)
EPA_TARGET_STATES = [
    "AL", "AR", "FL", "GA", "KY", "LA", "MS", "NC", "SC", "TN", "TX", "VA", "WV"
]


@router.get("/cron/sync", response_model=SyncResponse)
async def cron_sync_cases(
    states: Optional[str] = Query(None, description="Comma-separated state codes (defaults to SE+TX)"),
    days_back: int = Query(90, ge=1, le=365),
    min_penalty: float = Query(0, ge=0),
    x_cron_secret: Optional[str] = Header(None),
):
    """Cron-triggered EPA sync. Defaults to Southeast + Texas states."""
    if settings.CRON_SECRET and x_cron_secret != settings.CRON_SECRET:
        raise HTTPException(status_code=401, detail="Invalid cron secret")

    # Default to target states if none specified
    state_list = [s.strip().upper() for s in states.split(",")] if states else EPA_TARGET_STATES

    # Create cron run record and release connection before sync
    # to avoid connection pool exhaustion (pool size = 1)
    with get_db_session() as db:
        run = CronRun(job_name="epa", status="running")
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id  # Save ID before session closes

    try:
        stats = await epa_sync_service.sync_cases_bulk(
            states=state_list,
            days_back=days_back,
            min_penalty=min_penalty,
        )
        # Re-fetch run in new session to update status
        with get_db_session() as db:
            run = db.query(CronRun).filter(CronRun.id == run_id).first()
            if run:
                run.status = "success"
                run.finished_at = datetime.utcnow()
                run.details = json.dumps(stats)
                db.commit()

        return SyncResponse(
            success=True,
            message=f"EPA sync completed ({days_back} days back)",
            stats=stats,
        )
    except Exception as exc:
        with get_db_session() as db:
            run = db.query(CronRun).filter(CronRun.id == run_id).first()
            if run:
                run.status = "failed"
                run.finished_at = datetime.utcnow()
                run.error = str(exc)
                db.commit()
        raise


@router.get("/date-range")
async def get_date_range():
    """Get the date range of EPA cases in the database."""
    with get_db_session() as db:
        earliest = db.query(func.min(EPACase.date_filed)).scalar()
        latest = db.query(func.max(EPACase.date_filed)).scalar()
        total = db.query(func.count(EPACase.id)).scalar()

        return {
            "earliest_date": earliest.isoformat() if earliest else None,
            "latest_date": latest.isoformat() if latest else None,
            "total_cases": total or 0
        }


@router.get("/recent")
async def get_recent_cases(days: int = Query(30, ge=1, le=365)):
    """Get recently filed cases."""
    with get_db_session() as db:
        cutoff = datetime.now() - timedelta(days=days)
        cases = db.query(EPACase).filter(
            EPACase.date_filed >= cutoff.date()
        ).order_by(
            desc(EPACase.date_filed)
        ).limit(50).all()

        return {
            "count": len(cases),
            "days": days,
            "items": [case_to_response(c) for c in cases]
        }


@router.get("/{case_id}", response_model=EPACaseResponse)
async def get_case(case_id: int):
    """Get a specific EPA case by ID."""
    with get_db_session() as db:
        case = db.query(EPACase).filter(EPACase.id == case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        return case_to_response(case)
