"""EPA ECHO Enforcement Case sync service."""
import asyncio
import csv
import io
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import httpx

# Rate limiting between API calls (seconds)
EPA_API_DELAY = 0.5

from src.database.connection import get_db_session
from src.database.models import EPACase

logger = logging.getLogger(__name__)

# EPA ECHO API base URL
EPA_API_BASE = "https://echodata.epa.gov/echo"

# All columns available from ECHO API (by index for qcolumns parameter)
# 1=CaseNumber, 2=CaseName, 3=CaseCategoryCode, 4=CaseCategoryDesc, 5=CaseStatusCode,
# 6=CaseStatusDesc, 7=DOJDocketNmbr, 8=CourtDocketNumber, 9=PrimaryLaw, 10=PrimarySection,
# 11=DateFiled, 12=SettlementDate, 13=FedPenalty, 14=SEPCost, 15=PrimaryNAICSCode,
# 16=PrimarySICCode, 17=ActivityID, 18=TotalCompActionAmt, 19=SettlementCnt, 20=TRIbalLandFlag,
# 21=FederalFlag, 22=MultimediaFlag, 23=Lead, 24=Region, 25=CivilCriminalIndicator,
# 26=LeadAgency, 27=StateLocPenaltyAmt, 28=CostRecovery, 29=DateLodged, 30=DateClosed,
# 31=EnfOutcome, 32=CAAFlag, 33=CWAFlag, 34=RCRAFlag, 35=SDWAFlag, 36=CERCLAFlag,
# 37=EPCRAFlag, 38=TSCAFlag, 39=FIFRAFlag, 40=FacilityName, 41=FacilityCity
EPA_COLUMNS = ",".join(str(i) for i in range(1, 42))


class EPASyncService:
    """Service to sync EPA enforcement cases from ECHO API."""

    def __init__(self):
        self.timeout = 120.0  # Longer timeout for CSV downloads

    async def fetch_cases(
        self,
        state: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        min_penalty: Optional[float] = None,
        law: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetch enforcement cases from EPA ECHO API using two-step query+download.

        The ECHO API requires:
        1. Query to get a QueryID and total count
        2. CSV download using the QueryID to get actual case data

        Args:
            state: State postal code (e.g., 'TX', 'CA')
            from_date: Start date in MM/DD/YYYY format
            to_date: End date in MM/DD/YYYY format
            min_penalty: Minimum federal penalty amount
            law: Statute code (CAA, CWA, RCRA, etc.)

        Returns:
            Dict with 'items' list and 'total' count
        """
        # Step 1: Get query ID
        params = {"output": "JSON"}

        if state:
            params["p_state"] = state
        if from_date:
            params["p_from_date"] = from_date
        if to_date:
            params["p_to_date"] = to_date
        if min_penalty:
            if min_penalty >= 2500000:
                params["p_fed_penalty"] = "GT2500000"
            elif min_penalty >= 1000000:
                params["p_fed_penalty"] = "GT1000000"
            elif min_penalty >= 500000:
                params["p_fed_penalty"] = "GT500000"
            elif min_penalty >= 100000:
                params["p_fed_penalty"] = "GT100000"
            elif min_penalty >= 50000:
                params["p_fed_penalty"] = "GT50000"
            elif min_penalty >= 5000:
                params["p_fed_penalty"] = "GT5000"
        if law:
            params["p_law"] = law

        query_url = f"{EPA_API_BASE}/case_rest_services.get_cases"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Get query ID
                response = await client.get(query_url, params=params)
                response.raise_for_status()
                data = response.json()

                results = data.get("Results", {})
                query_id = results.get("QueryID")
                query_rows = int(results.get("QueryRows", 0) or 0)

                if not query_id or query_rows == 0:
                    return {"items": [], "total": 0}

                logger.info(f"EPA query for state={state}: {query_rows} cases found (QueryID: {query_id})")

                # Step 2: Download CSV with case data
                download_url = f"{EPA_API_BASE}/case_rest_services.get_download"
                download_params = {
                    "output": "CSV",
                    "qid": query_id,
                    "qcolumns": EPA_COLUMNS,
                }

                csv_response = await client.get(download_url, params=download_params)
                csv_response.raise_for_status()

                # Parse CSV
                reader = csv.DictReader(io.StringIO(csv_response.text))
                cases = list(reader)

                return {
                    "items": cases,
                    "total": query_rows,
                }

        except Exception as e:
            logger.error(f"Error fetching EPA cases: {e}")
            return {"items": [], "total": 0, "error": str(e)}

    async def fetch_case_detail(self, case_number: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed information for a specific case."""
        url = f"{EPA_API_BASE}/case_rest_services.get_case_report"
        params = {
            "p_case_number": case_number,
            "output": "JSON"
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error fetching case detail for {case_number}: {e}")
            return None

    def _parse_date(self, date_str: Optional[str]):
        """Parse EPA date format (MM/DD/YYYY or YYYY-MM-DD). Returns date object or None."""
        if not date_str or not isinstance(date_str, str):
            return None
        date_str = date_str.strip()
        if not date_str:
            return None
        try:
            # Try MM/DD/YYYY format first
            return datetime.strptime(date_str, "%m/%d/%Y").date()
        except ValueError:
            try:
                # Try YYYY-MM-DD format
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                logger.warning(f"Could not parse date: {date_str}")
                return None

    def _parse_float(self, value: Any) -> float:
        """Parse float value, returning 0 if invalid."""
        if value is None:
            return 0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0

    def _parse_bool(self, value: Any) -> bool:
        """Parse boolean value from various formats."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.upper() in ("Y", "YES", "TRUE", "1")
        return bool(value)

    async def sync_cases(
        self,
        states: Optional[List[str]] = None,
        days_back: int = 90,
        min_penalty: float = 0
    ) -> Dict[str, int]:
        """
        Sync EPA enforcement cases to database.

        Args:
            states: List of state codes to sync (None = all states)
            days_back: Number of days back to fetch
            min_penalty: Minimum penalty threshold

        Returns:
            Dict with 'new', 'updated', 'errors' counts
        """
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%m/%d/%Y")
        to_date = datetime.now().strftime("%m/%d/%Y")

        stats = {"new": 0, "updated": 0, "errors": 0, "total_fetched": 0}

        # If no states specified, fetch all
        states_to_sync = states or [None]

        for state in states_to_sync:
            result = await self.fetch_cases(
                state=state,
                from_date=from_date,
                to_date=to_date,
                min_penalty=min_penalty if min_penalty > 0 else None,
            )

            if "error" in result or not result["items"]:
                if "error" in result:
                    logger.error(f"Error fetching cases for {state}: {result['error']}")
                continue

            stats["total_fetched"] += len(result["items"])

            # Process cases
            for case_data in result["items"]:
                try:
                    self._upsert_case(case_data, stats)
                except Exception as e:
                    logger.error(f"Error processing case: {e}")
                    stats["errors"] += 1

        logger.info(f"EPA sync complete: {stats}")
        return stats

    def _upsert_case(self, case_data: Dict[str, Any], stats: Dict[str, int]) -> None:
        """Insert or update a case in the database.

        CSV column names from ECHO API:
        - CaseNumber, CaseName, CaseCategoryCode, CaseCategoryDesc
        - CaseStatusCode, CaseStatusDesc, CivilCriminalIndicator
        - Lead, DateFiled, SettlementDate, DateLodged, DateClosed
        - FedPenalty, StateLocPenaltyAmt, CostRecovery, TotalCompActionAmt, SEPCost
        - PrimaryNAICSCode, PrimarySICCode, ActivityID
        - CAAFlag, CWAFlag, RCRAFlag, SDWAFlag, CerclaFlag, EpcraFlag, TscaFlag, FifraFlag
        - PrimaryLaw, PrimarySection, FederalFlag, TRIbalLandFlag
        - SettlementCnt, EnfOutcome
        """
        case_number = case_data.get("CaseNumber")
        if not case_number:
            return

        with get_db_session() as db:
            existing = db.query(EPACase).filter(EPACase.case_number == case_number).first()

            # Parse SettlementCnt safely
            settlement_cnt = case_data.get("SettlementCnt", "0") or "0"
            try:
                settlement_count = int(settlement_cnt)
            except (ValueError, TypeError):
                settlement_count = 0

            case_values = {
                "case_number": case_number,
                "activity_id": case_data.get("ActivityID"),
                "case_name": case_data.get("CaseName"),
                "case_category": case_data.get("CaseCategoryCode"),
                "case_category_desc": case_data.get("CaseCategoryDesc"),
                "case_status": case_data.get("CaseStatusCode"),
                "case_status_desc": case_data.get("CaseStatusDesc"),
                "civil_criminal": case_data.get("CivilCriminalIndicator"),
                "case_lead": case_data.get("Lead"),
                "date_filed": self._parse_date(case_data.get("DateFiled")),
                "settlement_date": self._parse_date(case_data.get("SettlementDate")),
                "date_lodged": self._parse_date(case_data.get("DateLodged")),
                "date_closed": self._parse_date(case_data.get("DateClosed")),
                "fed_penalty": self._parse_float(case_data.get("FedPenalty")),
                "state_local_penalty": self._parse_float(case_data.get("StateLocPenaltyAmt")),
                "cost_recovery": self._parse_float(case_data.get("CostRecovery")),
                "compliance_action_cost": self._parse_float(case_data.get("TotalCompActionAmt")),
                "sep_cost": self._parse_float(case_data.get("SEPCost")),
                "primary_naics": case_data.get("PrimaryNAICSCode"),
                "primary_sic": case_data.get("PrimarySICCode"),
                # Note: Facility info not available in basic CSV download
                "caa_flag": self._parse_bool(case_data.get("CAAFlag")),
                "cwa_flag": self._parse_bool(case_data.get("CWAFlag")),
                "rcra_flag": self._parse_bool(case_data.get("RCRAFlag")),
                "sdwa_flag": self._parse_bool(case_data.get("SDWAFlag")),
                "cercla_flag": self._parse_bool(case_data.get("CerclaFlag")),
                "epcra_flag": self._parse_bool(case_data.get("EpcraFlag")),
                "tsca_flag": self._parse_bool(case_data.get("TscaFlag")),
                "fifra_flag": self._parse_bool(case_data.get("FifraFlag")),
                "primary_law": case_data.get("PrimaryLaw"),
                "primary_section": case_data.get("PrimarySection"),
                "federal_facility": self._parse_bool(case_data.get("FederalFlag")),
                "tribal_land": self._parse_bool(case_data.get("TRIbalLandFlag")),
                "settlement_count": settlement_count,
                "enforcement_outcome": case_data.get("EnfOutcome"),
                "updated_at": datetime.utcnow(),
            }

            if existing:
                for key, value in case_values.items():
                    setattr(existing, key, value)
                stats["updated"] += 1
            else:
                case_values["created_at"] = datetime.utcnow()
                new_case = EPACase(**case_values)
                db.add(new_case)
                stats["new"] += 1

            db.commit()

    async def sync_cases_bulk(
        self,
        states: Optional[List[str]] = None,
        days_back: int = 90,
        min_penalty: float = 0
    ) -> Dict[str, Any]:
        """
        Bulk sync EPA enforcement cases using a single DB session and PostgreSQL upsert.

        This is much faster than sync_cases() which opens a session per case.

        Args:
            states: List of state codes to sync (None = all states)
            days_back: Number of days back to fetch
            min_penalty: Minimum penalty threshold

        Returns:
            Dict with 'new', 'updated', 'errors', 'total_fetched' counts
        """
        from sqlalchemy.dialects.postgresql import insert

        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%m/%d/%Y")
        to_date = datetime.now().strftime("%m/%d/%Y")

        stats = {"new": 0, "updated": 0, "errors": 0, "total_fetched": 0}

        # If no states specified, fetch all
        states_to_sync = states or [None]

        all_cases = []
        for i, state in enumerate(states_to_sync):
            # Rate limit between state fetches (skip delay on first request)
            if i > 0:
                logger.info(f"EPA bulk sync: Waiting {EPA_API_DELAY}s before next state...")
                await asyncio.sleep(EPA_API_DELAY)

            logger.info(f"EPA bulk sync: Fetching cases for state={state or 'ALL'} ({i+1}/{len(states_to_sync)})...")
            result = await self.fetch_cases(
                state=state,
                from_date=from_date,
                to_date=to_date,
                min_penalty=min_penalty if min_penalty > 0 else None,
            )

            if "error" in result:
                logger.error(f"Error fetching cases for {state}: {result['error']}")
                stats["errors"] += 1
                continue

            if result.get("items"):
                logger.info(f"EPA bulk sync: Got {len(result['items'])} cases for state={state or 'ALL'}")
                all_cases.extend(result["items"])

        stats["total_fetched"] = len(all_cases)

        if not all_cases:
            logger.info("No EPA cases to sync")
            return stats

        # Parse all cases into values dicts
        parsed_cases = []
        def safe_str(val, max_len=None):
            """Convert value to string, truncate if needed."""
            if val is None:
                return None
            s = str(val).strip() if val else None
            if s and max_len:
                s = s[:max_len]
            return s

        for case_data in all_cases:
            try:
                case_number = case_data.get("CaseNumber")
                if not case_number:
                    continue

                settlement_cnt = case_data.get("SettlementCnt", "0") or "0"
                try:
                    settlement_count = int(settlement_cnt)
                except (ValueError, TypeError):
                    settlement_count = 0

                parsed_cases.append({
                    "case_number": safe_str(case_number, 50),
                    "activity_id": safe_str(case_data.get("ActivityID"), 50),
                    "case_name": safe_str(case_data.get("CaseName"), 500),
                    "case_category": safe_str(case_data.get("CaseCategoryCode"), 10),
                    "case_category_desc": safe_str(case_data.get("CaseCategoryDesc"), 100),
                    "case_status": safe_str(case_data.get("CaseStatusCode"), 50),
                    "case_status_desc": safe_str(case_data.get("CaseStatusDesc"), 100),
                    "civil_criminal": safe_str(case_data.get("CivilCriminalIndicator"), 10),
                    "case_lead": safe_str(case_data.get("Lead"), 10),
                    "date_filed": self._parse_date(case_data.get("DateFiled")),
                    "settlement_date": self._parse_date(case_data.get("SettlementDate")),
                    "date_lodged": self._parse_date(case_data.get("DateLodged")),
                    "date_closed": self._parse_date(case_data.get("DateClosed")),
                    "fed_penalty": self._parse_float(case_data.get("FedPenalty")),
                    "state_local_penalty": self._parse_float(case_data.get("StateLocPenaltyAmt")),
                    "cost_recovery": self._parse_float(case_data.get("CostRecovery")),
                    "compliance_action_cost": self._parse_float(case_data.get("TotalCompActionAmt")),
                    "sep_cost": self._parse_float(case_data.get("SEPCost")),
                    "primary_naics": safe_str(case_data.get("PrimaryNAICSCode"), 10),
                    "primary_sic": safe_str(case_data.get("PrimarySICCode"), 10),
                    "caa_flag": self._parse_bool(case_data.get("CAAFlag")),
                    "cwa_flag": self._parse_bool(case_data.get("CWAFlag")),
                    "rcra_flag": self._parse_bool(case_data.get("RCRAFlag")),
                    "sdwa_flag": self._parse_bool(case_data.get("SDWAFlag")),
                    "cercla_flag": self._parse_bool(case_data.get("CerclaFlag")),
                    "epcra_flag": self._parse_bool(case_data.get("EpcraFlag")),
                    "tsca_flag": self._parse_bool(case_data.get("TscaFlag")),
                    "fifra_flag": self._parse_bool(case_data.get("FifraFlag")),
                    "primary_law": safe_str(case_data.get("PrimaryLaw"), 50),
                    "primary_section": safe_str(case_data.get("PrimarySection"), 100),
                    "federal_facility": self._parse_bool(case_data.get("FederalFlag")),
                    "tribal_land": self._parse_bool(case_data.get("TRIbalLandFlag")),
                    "settlement_count": settlement_count,
                    "enforcement_outcome": safe_str(case_data.get("EnfOutcome")),
                    "updated_at": datetime.utcnow(),
                    "created_at": datetime.utcnow(),
                })
            except Exception as e:
                logger.error(f"Error parsing case {case_data.get('CaseNumber', 'unknown')}: {e}")
                stats["errors"] += 1
                continue

        if not parsed_cases:
            logger.info("No valid EPA cases to sync")
            return stats

        # Deduplicate cases by case_number (same case can appear in multiple states)
        # Keep the last occurrence (most recent data)
        seen_case_numbers = {}
        for case in parsed_cases:
            seen_case_numbers[case["case_number"]] = case
        parsed_cases = list(seen_case_numbers.values())
        logger.info(f"EPA bulk sync: {len(parsed_cases)} unique cases after deduplication")

        logger.info(f"EPA bulk sync: Upserting {len(parsed_cases)} cases to database...")

        # Bulk upsert using PostgreSQL ON CONFLICT
        with get_db_session() as db:
            # Get existing case numbers to track new vs updated
            from sqlalchemy import select
            case_numbers = [c["case_number"] for c in parsed_cases]
            existing_cases = set(
                row[0] for row in db.execute(
                    select(EPACase.case_number).where(EPACase.case_number.in_(case_numbers))
                ).fetchall()
            )

            # Use PostgreSQL upsert
            stmt = insert(EPACase).values(parsed_cases)
            stmt = stmt.on_conflict_do_update(
                index_elements=['case_number'],
                set_={
                    'activity_id': stmt.excluded.activity_id,
                    'case_name': stmt.excluded.case_name,
                    'case_category': stmt.excluded.case_category,
                    'case_category_desc': stmt.excluded.case_category_desc,
                    'case_status': stmt.excluded.case_status,
                    'case_status_desc': stmt.excluded.case_status_desc,
                    'civil_criminal': stmt.excluded.civil_criminal,
                    'case_lead': stmt.excluded.case_lead,
                    'date_filed': stmt.excluded.date_filed,
                    'settlement_date': stmt.excluded.settlement_date,
                    'date_lodged': stmt.excluded.date_lodged,
                    'date_closed': stmt.excluded.date_closed,
                    'fed_penalty': stmt.excluded.fed_penalty,
                    'state_local_penalty': stmt.excluded.state_local_penalty,
                    'cost_recovery': stmt.excluded.cost_recovery,
                    'compliance_action_cost': stmt.excluded.compliance_action_cost,
                    'sep_cost': stmt.excluded.sep_cost,
                    'primary_naics': stmt.excluded.primary_naics,
                    'primary_sic': stmt.excluded.primary_sic,
                    'caa_flag': stmt.excluded.caa_flag,
                    'cwa_flag': stmt.excluded.cwa_flag,
                    'rcra_flag': stmt.excluded.rcra_flag,
                    'sdwa_flag': stmt.excluded.sdwa_flag,
                    'cercla_flag': stmt.excluded.cercla_flag,
                    'epcra_flag': stmt.excluded.epcra_flag,
                    'tsca_flag': stmt.excluded.tsca_flag,
                    'fifra_flag': stmt.excluded.fifra_flag,
                    'primary_law': stmt.excluded.primary_law,
                    'primary_section': stmt.excluded.primary_section,
                    'federal_facility': stmt.excluded.federal_facility,
                    'tribal_land': stmt.excluded.tribal_land,
                    'settlement_count': stmt.excluded.settlement_count,
                    'enforcement_outcome': stmt.excluded.enforcement_outcome,
                    'updated_at': stmt.excluded.updated_at,
                }
            )
            db.execute(stmt)
            db.commit()

            # Count new vs updated
            for c in parsed_cases:
                if c["case_number"] in existing_cases:
                    stats["updated"] += 1
                else:
                    stats["new"] += 1

        logger.info(f"EPA bulk sync complete: {stats}")
        return stats


# Singleton instance
epa_sync_service = EPASyncService()
