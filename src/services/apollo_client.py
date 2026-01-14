import httpx
import logging
from typing import List, Dict, Any, Optional

from src.config import settings

logger = logging.getLogger(__name__)


class ApolloClient:
    """Client for the Apollo.io API."""

    def __init__(self):
        self.base_url = settings.APOLLO_API_BASE_URL
        self.api_key = settings.APOLLO_API_KEY
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def search_organization(
        self,
        name: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Search for an organization by name and location.

        Args:
            name: Company name to search
            city: Optional city for more accurate matching
            state: Optional state for more accurate matching

        Returns:
            Organization data if found, None otherwise
        """
        url = f"{self.base_url}/organizations/search"

        # Build search query
        query = name
        if city:
            query += f" {city}"
        if state:
            query += f" {state}"

        payload = {
            "q_organization_name": name,
            "per_page": 5,  # Get top matches
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    url, headers=self.headers, json=payload
                )
                response.raise_for_status()
                data = response.json()

                organizations = data.get("organizations", [])
                if not organizations:
                    logger.info(f"No organization found for: {name}")
                    return None

                # Return best match (first result)
                org = organizations[0]
                logger.info(f"Found organization: {org.get('name')} for query: {name}")
                return org

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error searching organization '{name}': {e.response.status_code}"
                )
                if e.response.status_code == 429:
                    logger.warning("Rate limited by Apollo API")
                raise
            except httpx.RequestError as e:
                logger.error(f"Request error searching organization: {e}")
                raise

    async def enrich_organization(
        self,
        domain: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Enrich organization data by domain or name.

        Args:
            domain: Company website domain
            name: Company name (used if domain not available)

        Returns:
            Enriched organization data
        """
        url = f"{self.base_url}/organizations/enrich"

        params = {}
        if domain:
            params["domain"] = domain
        elif name:
            params["name"] = name
        else:
            raise ValueError("Either domain or name must be provided")

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    url, headers=self.headers, params=params
                )
                response.raise_for_status()
                data = response.json()

                org = data.get("organization")
                if org:
                    logger.info(f"Enriched organization: {org.get('name')}")
                return org

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error enriching organization: {e.response.status_code}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Request error enriching organization: {e}")
                raise

    async def search_people(
        self,
        organization_name: Optional[str] = None,
        organization_domain: Optional[str] = None,
        titles: Optional[List[str]] = None,
        limit: int = 25,
    ) -> List[Dict[str, Any]]:
        """
        Search for people at a company matching specified job titles.

        Args:
            organization_name: Company name
            organization_domain: Company domain
            titles: List of job titles to search for
            limit: Maximum results to return

        Returns:
            List of matching people
        """
        # Use the new api_search endpoint (mixed_people/search is deprecated)
        url = f"{self.base_url}/mixed_people/api_search"

        # Include api_key in body as some Apollo endpoints require it
        payload = {
            "api_key": self.api_key,
            "per_page": min(limit, 100),
            "page": 1,
        }

        if organization_domain:
            # q_organization_domains for searching people at a company
            payload["q_organization_domains"] = organization_domain
        elif organization_name:
            payload["q_organization_name"] = organization_name
        else:
            raise ValueError("Either organization_name or organization_domain required")

        if titles:
            # person_titles should be an array of strings
            payload["person_titles"] = titles

        logger.info(f"Apollo people search payload (api_key hidden): domain={organization_domain}, titles_count={len(titles) if titles else 0}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    url, headers=self.headers, json=payload
                )

                # Log response for debugging
                if response.status_code != 200:
                    logger.error(f"Apollo people search response: {response.text}")

                response.raise_for_status()
                data = response.json()

                people = data.get("people", [])
                logger.info(
                    f"Found {len(people)} people at "
                    f"{organization_domain or organization_name}"
                )
                return people

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error searching people: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
                if e.response.status_code == 429:
                    logger.warning("Rate limited by Apollo API")
                raise
            except httpx.RequestError as e:
                logger.error(f"Request error searching people: {e}")
                raise

    async def search_contacts_by_titles(
        self,
        organization_name: str,
        organization_domain: Optional[str] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search for both safety roles and executives at a company.

        Args:
            organization_name: Company name
            organization_domain: Company domain (preferred for accuracy)

        Returns:
            Dict with 'safety_contacts' and 'executive_contacts' lists
        """
        all_titles = settings.SAFETY_TITLES + settings.EXECUTIVE_TITLES

        people = await self.search_people(
            organization_name=organization_name,
            organization_domain=organization_domain,
            titles=all_titles,
            limit=50,
        )

        # Categorize contacts
        safety_contacts = []
        executive_contacts = []

        safety_keywords = [t.lower() for t in settings.SAFETY_TITLES]
        executive_keywords = [t.lower() for t in settings.EXECUTIVE_TITLES]

        for person in people:
            title = (person.get("title") or "").lower()

            is_safety = any(kw.lower() in title for kw in safety_keywords)
            is_exec = any(kw.lower() in title for kw in executive_keywords)

            if is_safety:
                safety_contacts.append(person)
            if is_exec:
                executive_contacts.append(person)

        return {
            "safety_contacts": safety_contacts,
            "executive_contacts": executive_contacts,
        }

    def parse_organization(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw Apollo organization data into our model format."""
        return {
            "apollo_org_id": raw.get("id"),
            "name": raw.get("name", ""),
            "domain": raw.get("primary_domain") or raw.get("website_url", "").replace("https://", "").replace("http://", "").split("/")[0],
            "website": raw.get("website_url"),
            "industry": raw.get("industry"),
            "sub_industry": raw.get("subindustry"),
            "employee_count": raw.get("estimated_num_employees"),
            "employee_range": raw.get("employee_range"),
            "annual_revenue": raw.get("annual_revenue"),
            "revenue_range": raw.get("annual_revenue_printed"),
            "phone": raw.get("phone"),
            "linkedin_url": raw.get("linkedin_url"),
            "facebook_url": raw.get("facebook_url"),
            "twitter_url": raw.get("twitter_url"),
            "address": raw.get("street_address"),
            "city": raw.get("city"),
            "state": raw.get("state"),
            "postal_code": raw.get("postal_code"),
            "country": raw.get("country"),
        }

    def parse_person(self, raw: Dict[str, Any], contact_type: str) -> Dict[str, Any]:
        """Parse raw Apollo person data into our model format."""
        # Build full name from first/last if 'name' field is missing
        first_name = raw.get("first_name") or ""
        last_name = raw.get("last_name") or ""
        full_name = raw.get("name") or f"{first_name} {last_name}".strip()

        # If still no name, try organization_name as fallback context
        if not full_name:
            full_name = "Unknown Contact"

        return {
            "apollo_person_id": raw.get("id"),
            "first_name": first_name or None,
            "last_name": last_name or None,
            "full_name": full_name,
            "title": raw.get("title"),
            "email": raw.get("email"),
            "email_status": raw.get("email_status"),
            "phone": raw.get("phone_numbers", [{}])[0].get("raw_number") if raw.get("phone_numbers") else None,
            "mobile_phone": raw.get("mobile_phone"),
            "linkedin_url": raw.get("linkedin_url"),
            "seniority": raw.get("seniority"),
            "departments": ",".join(raw.get("departments", [])) if raw.get("departments") else None,
            "contact_type": contact_type,
        }

    async def reveal_contact_info(
        self,
        person_id: str,
        reveal_email: bool = True,
        reveal_phone: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Reveal email and/or phone for a specific person (uses credits).

        Note: Phone reveal requires a webhook_url which we don't currently support.

        Args:
            person_id: Apollo person ID
            reveal_email: Whether to reveal email (default True)
            reveal_phone: Whether to attempt phone reveal (requires webhook setup)

        Returns:
            Person data with revealed email/phone
        """
        url = f"{self.base_url}/people/match"

        payload = {
            "api_key": self.api_key,
            "id": person_id,
        }

        # Add email reveal if requested
        if reveal_email:
            payload["reveal_personal_emails"] = True

        # Phone reveal requires webhook_url - warn user but still try if requested
        if reveal_phone:
            logger.warning("Phone reveal requested - requires webhook_url to receive async phone data")
            # Uncomment below when webhook is configured:
            # payload["reveal_phone_number"] = True
            # payload["webhook_url"] = "https://your-domain.com/api/webhooks/apollo"

        reveal_types = []
        if reveal_email:
            reveal_types.append("email")
        if reveal_phone:
            reveal_types.append("phone")

        logger.info(f"Revealing {', '.join(reveal_types) or 'nothing'} for person_id: {person_id}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    url, headers=self.headers, json=payload
                )

                if response.status_code != 200:
                    logger.error(f"Apollo reveal response: {response.text}")

                response.raise_for_status()
                data = response.json()

                person = data.get("person")
                if person:
                    logger.info(f"Revealed contact info for: {person.get('name')} - email: {person.get('email')}")
                return person

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error revealing contact: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Request error revealing contact: {e}")
                raise

    async def bulk_reveal_contacts(self, person_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Reveal email and phone for multiple people (uses credits per person).

        Args:
            person_ids: List of Apollo person IDs

        Returns:
            List of person data with revealed email/phone
        """
        revealed = []
        for person_id in person_ids:
            try:
                person = await self.reveal_contact_info(person_id)
                if person:
                    revealed.append(person)
            except Exception as e:
                logger.error(f"Failed to reveal contact {person_id}: {e}")
                # Continue with other contacts
        return revealed
