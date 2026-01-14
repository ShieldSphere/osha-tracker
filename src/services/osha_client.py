"""
OSHA DOL API Client

Fetches inspection and violation data from the DOL OSHA Enforcement API.
Uses filter_object for server-side filtering and includes rate limiting guardrails.

API Documentation: http://developer.dol.gov/health-and-safety/dol-osha-enforcement
"""
import httpx
import asyncio
import logging
import json
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from src.config import settings

if TYPE_CHECKING:
    from src.services.sync_service import LogCollector

logger = logging.getLogger(__name__)

# =============================================================================
# RATE LIMITING CONFIGURATION
# =============================================================================
API_DELAY = 0.5  # Seconds between requests (reduced for serverless - was 3.0)
MAX_RECORDS_PER_REQUEST = 200  # API limit per request (DOL allows up to 200)
MAX_REQUESTS_PER_RUN = 50  # Prevent runaway API calls
ACTIVITY_NR_BATCH_SIZE = 100  # Max activity_nrs per "in" filter request

# Exponential backoff for 429 responses
BACKOFF_DELAYS = [30, 60, 120]  # Seconds to wait on each retry


class OSHAClient:
    """
    Client for the DOL OSHA Enforcement API.

    Features:
    - Server-side filtering using filter_object parameter
    - Exponential backoff on rate limit (429) responses
    - Request counting and logging for debugging
    - Configurable guardrails to prevent excessive API calls
    """

    def __init__(self):
        self.base_url = "https://apiprod.dol.gov/v4/get/OSHA"
        self.api_key = settings.DOL_API_KEY
        self.request_count = 0  # Track requests in this session

    def _log_request(self, endpoint: str, params: dict, note: str = "", log_collector: Optional["LogCollector"] = None):
        """Log API request with timestamp for debugging."""
        self.request_count += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filter_info = params.get("filter_object", "none")
        msg = (
            f"API Request #{self.request_count}: {endpoint} | "
            f"limit={params.get('limit')} offset={params.get('offset')} | "
            f"filter={filter_info[:50]}... | {note}"
        )
        logger.info(f"[{timestamp}] {msg}")
        if log_collector:
            log_collector.log(msg)

    async def _make_request(
        self,
        endpoint: str,
        params: dict,
        note: str = "",
        log_collector: Optional["LogCollector"] = None
    ) -> List[Dict[str, Any]]:
        """
        Make an API request with exponential backoff on rate limits.

        Args:
            endpoint: API endpoint (e.g., "inspection/json")
            params: Query parameters
            note: Optional note for logging
            log_collector: Optional LogCollector for response logging

        Returns:
            List of records from API response
        """
        url = f"{self.base_url}/{endpoint}"
        params["X-API-KEY"] = self.api_key

        self._log_request(endpoint, params, note, log_collector)

        if log_collector:
            log_collector.log(f"Making request to: {url}")

        async with httpx.AsyncClient(timeout=120.0, verify=False) as client:
            for attempt, backoff in enumerate(BACKOFF_DELAYS + [None]):
                try:
                    response = await client.get(url, params=params)

                    if log_collector:
                        log_collector.log(f"Response status: {response.status_code}")

                    response.raise_for_status()

                    # Handle 204 No Content (no matching records)
                    if response.status_code == 204 or not response.text:
                        msg = "No records found (204 No Content)"
                        logger.info(f"  -> {msg}")
                        if log_collector:
                            log_collector.log(msg)
                        return []

                    result = response.json()

                    # API returns data in a 'data' key
                    data = result.get("data", []) if isinstance(result, dict) else result
                    msg = f"Received {len(data)} records"
                    logger.info(f"  -> {msg}")
                    if log_collector:
                        log_collector.log(msg)
                    return data

                except httpx.HTTPStatusError as e:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                    if log_collector:
                        log_collector.error(error_msg)

                    if e.response.status_code == 429:
                        if backoff is None:
                            msg = f"Rate limited after {len(BACKOFF_DELAYS)} retries, giving up"
                            logger.error(msg)
                            if log_collector:
                                log_collector.error(msg)
                            return []
                        msg = f"Rate limited (429), attempt {attempt + 1}/{len(BACKOFF_DELAYS)}. Waiting {backoff}s..."
                        logger.warning(msg)
                        if log_collector:
                            log_collector.log(msg)
                        await asyncio.sleep(backoff)
                        continue
                    elif e.response.status_code == 401:
                        msg = "Authentication failed - check DOL_API_KEY"
                        logger.error(msg)
                        if log_collector:
                            log_collector.error(msg)
                        raise
                    elif e.response.status_code == 403:
                        msg = "Access forbidden - API key may not have access to this endpoint"
                        logger.error(msg)
                        if log_collector:
                            log_collector.error(msg)
                        raise
                    else:
                        logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
                        raise

                except httpx.RequestError as e:
                    msg = f"Request error: {type(e).__name__}: {str(e)}"
                    logger.error(msg)
                    if log_collector:
                        log_collector.error(msg)
                    raise

        return []

    async def fetch_inspections_since(
        self,
        since_date: date,
        limit: int = MAX_RECORDS_PER_REQUEST,
        offset: int = 0,
        log_collector: Optional["LogCollector"] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch inspections with open_date > since_date using server-side filtering.

        Args:
            since_date: Only fetch inspections opened AFTER this date
            limit: Records per request (max 200)
            offset: Pagination offset
            log_collector: Optional LogCollector for response logging

        Returns:
            List of inspection records
        """
        # Format date as MM/DD/YYYY for DOL API filter
        date_str = since_date.strftime("%m/%d/%Y")

        # Build filter_object for server-side filtering
        filter_object = {
            "field": "open_date",
            "operator": "gt",
            "value": date_str
        }

        params = {
            "limit": min(limit, MAX_RECORDS_PER_REQUEST),
            "offset": offset,
            "filter_object": json.dumps(filter_object),
        }

        return await self._make_request(
            "inspection/json",
            params,
            note=f"open_date > {date_str}",
            log_collector=log_collector
        )

    async def fetch_violations_for_activity_nrs(
        self,
        activity_nrs: List[str],
        limit: int = MAX_RECORDS_PER_REQUEST,
        offset: int = 0,
        log_collector: Optional["LogCollector"] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch violations for multiple inspections using "in" filter.

        Args:
            activity_nrs: List of activity numbers to fetch violations for
            limit: Records per request (max 200)
            offset: Pagination offset
            log_collector: Optional LogCollector for response logging

        Returns:
            List of violation records
        """
        if not activity_nrs:
            return []

        # Build filter_object with "in" operator
        filter_object = {
            "field": "activity_nr",
            "operator": "in",
            "value": activity_nrs
        }

        params = {
            "limit": min(limit, MAX_RECORDS_PER_REQUEST),
            "offset": offset,
            "filter_object": json.dumps(filter_object),
        }

        return await self._make_request(
            "violation/json",
            params,
            note=f"{len(activity_nrs)} activity_nrs",
            log_collector=log_collector
        )

    async def fetch_all_new_inspections(
        self,
        since_date: date,
        max_requests: int = MAX_REQUESTS_PER_RUN,
        log_collector: Optional["LogCollector"] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch ALL inspections with open_date > since_date.

        Paginates through results until no more records or max_requests reached.

        Args:
            since_date: Only fetch inspections opened AFTER this date
            max_requests: Maximum API requests to prevent runaway calls
            log_collector: Optional LogCollector for response logging

        Returns:
            List of all matching inspection records
        """
        all_inspections = []
        offset = 0
        requests_made = 0

        msg1 = f"Fetching inspections with open_date > {since_date}"
        msg2 = f"Rate limiting: {API_DELAY}s between requests, max {max_requests} requests"
        logger.info(msg1)
        logger.info(msg2)
        if log_collector:
            log_collector.log(msg1)
            log_collector.log(msg2)

        while requests_made < max_requests:
            batch = await self.fetch_inspections_since(
                since_date=since_date,
                limit=MAX_RECORDS_PER_REQUEST,
                offset=offset,
                log_collector=log_collector,
            )
            requests_made += 1

            if not batch:
                msg = f"No more records at offset {offset}"
                logger.info(msg)
                if log_collector:
                    log_collector.log(msg)
                break

            all_inspections.extend(batch)
            offset += len(batch)

            msg = f"Progress: {len(all_inspections)} total inspections fetched"
            logger.info(msg)
            if log_collector:
                log_collector.log(msg)

            # If we got fewer than requested, we've reached the end
            if len(batch) < MAX_RECORDS_PER_REQUEST:
                msg = "Reached end of results"
                logger.info(msg)
                if log_collector:
                    log_collector.log(msg)
                break

            # Rate limiting delay
            if log_collector:
                log_collector.log(f"Waiting {API_DELAY}s before next request...")
            await asyncio.sleep(API_DELAY)

        if requests_made >= max_requests:
            msg = f"Reached max requests limit ({max_requests})"
            logger.warning(msg)
            if log_collector:
                log_collector.log(msg)

        msg = f"Completed: {len(all_inspections)} inspections fetched in {requests_made} requests"
        logger.info(msg)
        if log_collector:
            log_collector.log(msg)
        return all_inspections

    async def fetch_all_violations_for_inspections(
        self,
        activity_nrs: List[str],
        max_requests: int = MAX_REQUESTS_PER_RUN,
        log_collector: Optional["LogCollector"] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch violations for a list of inspections.

        Batches activity_nrs into groups and paginates each batch.

        Args:
            activity_nrs: List of inspection activity numbers
            max_requests: Maximum API requests to prevent runaway calls
            log_collector: Optional LogCollector for response logging

        Returns:
            List of all violation records
        """
        if not activity_nrs:
            return []

        all_violations = []
        requests_made = 0

        # Batch activity_nrs into chunks
        batches = [
            activity_nrs[i:i + ACTIVITY_NR_BATCH_SIZE]
            for i in range(0, len(activity_nrs), ACTIVITY_NR_BATCH_SIZE)
        ]

        msg = (
            f"Fetching violations for {len(activity_nrs)} inspections "
            f"in {len(batches)} batches of up to {ACTIVITY_NR_BATCH_SIZE}"
        )
        logger.info(msg)
        if log_collector:
            log_collector.log(msg)

        for batch_num, batch_nrs in enumerate(batches):
            if requests_made >= max_requests:
                msg = f"Reached max requests limit ({max_requests})"
                logger.warning(msg)
                if log_collector:
                    log_collector.log(msg)
                break

            msg = f"Processing batch {batch_num + 1}/{len(batches)}"
            logger.info(msg)
            if log_collector:
                log_collector.log(msg)

            # Paginate through this batch
            offset = 0
            while requests_made < max_requests:
                violations = await self.fetch_violations_for_activity_nrs(
                    activity_nrs=batch_nrs,
                    limit=MAX_RECORDS_PER_REQUEST,
                    offset=offset,
                    log_collector=log_collector,
                )
                requests_made += 1

                if not violations:
                    break

                all_violations.extend(violations)
                offset += len(violations)

                # If we got fewer than requested, we've got all for this batch
                if len(violations) < MAX_RECORDS_PER_REQUEST:
                    break

                # Rate limiting delay
                await asyncio.sleep(API_DELAY)

            # Delay between batches
            if batch_num < len(batches) - 1:
                await asyncio.sleep(API_DELAY)

        msg = f"Completed: {len(all_violations)} violations fetched in {requests_made} requests"
        logger.info(msg)
        if log_collector:
            log_collector.log(msg)
        return all_violations

    # =========================================================================
    # LEGACY METHODS (kept for backwards compatibility)
    # =========================================================================

    async def fetch_inspections(
        self,
        limit: int = 100,
        offset: int = 0,
        since_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """
        Legacy method: Fetch inspections without server-side filtering.
        Use fetch_inspections_since() for filtered queries.
        """
        params = {
            "limit": min(limit, MAX_RECORDS_PER_REQUEST),
            "offset": offset,
        }
        return await self._make_request("inspection/json", params, note="legacy/no filter")

    async def fetch_violations_for_inspection(
        self,
        activity_nr: str,
    ) -> List[Dict[str, Any]]:
        """
        Legacy method: Fetch violations for a single inspection.
        Use fetch_violations_for_activity_nrs() for batch fetching.
        """
        return await self.fetch_violations_for_activity_nrs([activity_nr])

    def parse_inspection(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse raw API response into standardized inspection data.

        Args:
            raw: Raw inspection record from API

        Returns:
            Parsed inspection data matching our database model
        """

        def safe_date(value: Any) -> Optional[date]:
            if not value:
                return None
            if isinstance(value, date):
                return value
            try:
                # Handle ISO format: 2016-06-08T00:00:00
                return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass
            try:
                # Handle MM/DD/YYYY format
                return datetime.strptime(str(value).strip(), "%m/%d/%Y").date()
            except (ValueError, TypeError):
                return None

        def safe_str(value: Any) -> Optional[str]:
            if value is None:
                return None
            s = str(value).strip()
            return s if s else None

        def safe_int(value: Any) -> Optional[int]:
            if value is None:
                return None
            try:
                return int(value)
            except (ValueError, TypeError):
                return None

        def safe_datetime(value: Any) -> Optional[datetime]:
            if not value:
                return None
            if isinstance(value, datetime):
                return value
            try:
                val_str = str(value).strip()
                # Remove timezone suffix if present
                for tz in [' EST', ' PST', ' CST', ' MST', ' EDT', ' PDT', ' CDT', ' MDT']:
                    val_str = val_str.replace(tz, '')
                # Try ISO format with T separator
                if 'T' in val_str:
                    return datetime.strptime(val_str[:19], "%Y-%m-%dT%H:%M:%S")
                # Try space separator
                elif len(val_str) >= 19:
                    return datetime.strptime(val_str[:19], "%Y-%m-%d %H:%M:%S")
                else:
                    return datetime.strptime(val_str[:10], "%Y-%m-%d")
            except (ValueError, TypeError):
                return None

        return {
            "activity_nr": str(raw.get("activity_nr", "")),
            "reporting_id": safe_str(raw.get("reporting_id")),
            "state_flag": safe_str(raw.get("state_flag")),
            "estab_name": safe_str(raw.get("estab_name")) or "",
            "site_address": safe_str(raw.get("site_address")),
            "site_city": safe_str(raw.get("site_city")),
            "site_state": safe_str(raw.get("site_state")),
            "site_zip": safe_str(raw.get("site_zip")),
            "mail_street": safe_str(raw.get("mail_street")),
            "mail_city": safe_str(raw.get("mail_city")),
            "mail_state": safe_str(raw.get("mail_state")),
            "mail_zip": safe_str(raw.get("mail_zip")),
            "open_date": safe_date(raw.get("open_date")),
            "case_mod_date": safe_date(raw.get("case_mod_date")),
            "close_conf_date": safe_date(raw.get("close_conf_date")),
            "close_case_date": safe_date(raw.get("close_case_date")),
            "sic_code": safe_str(raw.get("sic_code")),
            "naics_code": safe_str(raw.get("naics_code")),
            "insp_type": safe_str(raw.get("insp_type")),
            "insp_scope": safe_str(raw.get("insp_scope")),
            "why_no_insp": safe_str(raw.get("why_no_insp")),
            "owner_type": safe_str(raw.get("owner_type")),
            "owner_code": safe_str(raw.get("owner_code")),
            "adv_notice": safe_str(raw.get("adv_notice")),
            "safety_hlth": safe_str(raw.get("safety_hlth")),
            "union_status": safe_str(raw.get("union_status")),
            "safety_manuf": safe_str(raw.get("safety_manuf")),
            "safety_const": safe_str(raw.get("safety_const")),
            "safety_marit": safe_str(raw.get("safety_marit")),
            "health_manuf": safe_str(raw.get("health_manuf")),
            "health_const": safe_str(raw.get("health_const")),
            "health_marit": safe_str(raw.get("health_marit")),
            "migrant": safe_str(raw.get("migrant")),
            "nr_in_estab": safe_int(raw.get("nr_in_estab")),
            "host_est_key": safe_str(raw.get("host_est_key")),
            "load_dt": safe_datetime(raw.get("load_dt") or raw.get("ld_dt")),
            "total_current_penalty": None,
            "total_initial_penalty": None,
        }

    def parse_violation(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse raw API violation response into standardized data.

        Args:
            raw: Raw violation record from API

        Returns:
            Parsed violation data matching our database model
        """

        def safe_date(value: Any) -> Optional[date]:
            if not value:
                return None
            try:
                return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass
            try:
                return datetime.strptime(str(value).strip(), "%m/%d/%Y").date()
            except (ValueError, TypeError):
                return None

        def safe_str(value: Any) -> Optional[str]:
            if value is None:
                return None
            s = str(value).strip()
            return s if s else None

        def safe_float(value: Any) -> float:
            try:
                return float(value) if value else 0.0
            except (ValueError, TypeError):
                return 0.0

        def safe_int(value: Any) -> Optional[int]:
            try:
                return int(value) if value else None
            except (ValueError, TypeError):
                return None

        return {
            "activity_nr": str(raw.get("activity_nr", "")),
            "citation_id": safe_str(raw.get("citation_id")) or "",
            "delete_flag": safe_str(raw.get("delete_flag")),
            "standard": safe_str(raw.get("standard")),
            "viol_type": safe_str(raw.get("viol_type")),
            "issuance_date": safe_date(raw.get("issuance_date")),
            "abate_date": safe_date(raw.get("abate_date")),
            "abate_complete": safe_str(raw.get("abate_complete")),
            "current_penalty": safe_float(raw.get("current_penalty")),
            "initial_penalty": safe_float(raw.get("initial_penalty")),
            "contest_date": safe_date(raw.get("contest_date")),
            "final_order_date": safe_date(raw.get("final_order_date")),
            "nr_instances": safe_int(raw.get("nr_instances")) or 1,
            "nr_exposed": safe_int(raw.get("nr_exposed")) or 0,
            "rec": safe_str(raw.get("rec")),
            "gravity": safe_str(raw.get("gravity")),
            "emphasis": safe_str(raw.get("emphasis")),
            "hazcat": safe_str(raw.get("hazcat")),
            "fta_insp_nr": safe_str(raw.get("fta_insp_nr")),
            "fta_issuance_date": safe_date(raw.get("fta_issuance_date")),
            "fta_penalty": safe_float(raw.get("fta_penalty")) if raw.get("fta_penalty") else None,
            "fta_contest_date": safe_date(raw.get("fta_contest_date")),
            "fta_final_order_date": safe_date(raw.get("fta_final_order_date")),
            "hazsub1": safe_str(raw.get("hazsub1")),
            "hazsub2": safe_str(raw.get("hazsub2")),
            "hazsub3": safe_str(raw.get("hazsub3")),
            "hazsub4": safe_str(raw.get("hazsub4")),
            "hazsub5": safe_str(raw.get("hazsub5")),
        }
