"""Public enrichment service using free/public data sources."""
import logging
import re
from typing import Optional, Dict, Any, List

import httpx

from src.config import settings
from src.services.company_normalizer import normalize_company_name

logger = logging.getLogger(__name__)


class PublicEnrichmentService:
    """Service to enrich company data from public sources (OSM + OpenCorporates)."""

    def __init__(self) -> None:
        self.nominatim_url = "https://nominatim.openstreetmap.org/search"
        self.opencorporates_url = "https://api.opencorporates.com/v0.4"
        self.user_agent = "TSG Safety OSHA Tracker (public enrichment)"

    def _normalize(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()

    def _score_name_match(self, target: str, candidate: str) -> int:
        if not target or not candidate:
            return 0
        target_norm = self._normalize(target)
        candidate_norm = self._normalize(candidate)
        if not target_norm or not candidate_norm:
            return 0
        if target_norm == candidate_norm:
            return 5
        if target_norm in candidate_norm or candidate_norm in target_norm:
            return 3
        return 0

    def _score_location_match(self, candidate: Dict[str, Any], city: Optional[str], state: Optional[str]) -> int:
        score = 0
        address = candidate.get("address") or {}
        candidate_city = address.get("city") or address.get("town") or address.get("village")
        candidate_state = address.get("state") or address.get("state_code")
        if city and candidate_city and self._normalize(city) == self._normalize(candidate_city):
            score += 2
        if state and candidate_state and self._normalize(state) == self._normalize(candidate_state):
            score += 2
        return score

    def _map_osm_industry(self, osm_class: Optional[str], osm_type: Optional[str]) -> Optional[str]:
        if not osm_class and not osm_type:
            return None
        key = f"{osm_class}:{osm_type}".lower()
        mapping = {
            "amenity:restaurant": "Restaurant",
            "amenity:cafe": "Cafe",
            "amenity:bar": "Hospitality",
            "amenity:school": "Education",
            "amenity:hospital": "Healthcare",
            "amenity:clinic": "Healthcare",
            "shop:supermarket": "Retail",
            "shop:convenience": "Retail",
            "shop:clothes": "Retail",
            "shop:hardware": "Retail",
            "shop:car_repair": "Automotive",
            "industrial:factory": "Manufacturing",
            "industrial:warehouse": "Logistics",
            "office:company": "Professional Services",
            "office:it": "Technology",
            "office:construction": "Construction",
        }
        return mapping.get(key) or f"{osm_class or 'unknown'} / {osm_type or 'unknown'}"

    async def _nominatim_search(self, company_name: str, city: Optional[str], state: Optional[str]) -> List[Dict[str, Any]]:
        query = " ".join([p for p in [company_name, city, state] if p])
        params = {
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "extratags": 1,
            "namedetails": 1,
            "limit": 5,
        }
        if settings.NOMINATIM_EMAIL:
            params["email"] = settings.NOMINATIM_EMAIL

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(self.nominatim_url, params=params, headers={"User-Agent": self.user_agent})
                response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else []
        except Exception as exc:
            logger.error(f"Nominatim search error: {exc}")
            return []

    async def _opencorporates_search(self, company_name: str, state: Optional[str]) -> List[Dict[str, Any]]:
        if not settings.OPENCORPORATES_API_KEY:
            return []
        params = {"q": company_name, "per_page": 5}
        if state:
            params["jurisdiction_code"] = f"us_{state.lower()}"
        if settings.OPENCORPORATES_API_KEY:
            params["api_token"] = settings.OPENCORPORATES_API_KEY

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(f"{self.opencorporates_url}/companies/search", params=params, headers={"User-Agent": self.user_agent})
                response.raise_for_status()
            data = response.json()
            return data.get("results", {}).get("companies", []) if isinstance(data, dict) else []
        except Exception as exc:
            logger.error(f"OpenCorporates search error: {exc}")
            return []

    async def _opencorporates_officers(self, jurisdiction_code: str, company_number: str) -> List[Dict[str, Any]]:
        if not settings.OPENCORPORATES_API_KEY:
            return []
        params = {}
        if settings.OPENCORPORATES_API_KEY:
            params["api_token"] = settings.OPENCORPORATES_API_KEY

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    f"{self.opencorporates_url}/companies/{jurisdiction_code}/{company_number}/officers",
                    params=params,
                    headers={"User-Agent": self.user_agent},
                )
                response.raise_for_status()
            data = response.json()
            return data.get("results", {}).get("officers", []) if isinstance(data, dict) else []
        except Exception as exc:
            logger.error(f"OpenCorporates officers error: {exc}")
            return []

    def _best_nominatim_candidate(
        self,
        candidates: List[Dict[str, Any]],
        company_name: str,
        city: Optional[str],
        state: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        best = None
        best_score = 0
        for candidate in candidates:
            name = candidate.get("namedetails", {}).get("name") or candidate.get("display_name", "")
            score = self._score_name_match(company_name, name)
            score += self._score_location_match(candidate, city, state)
            if score > best_score:
                best_score = score
                best = candidate
        return best if best_score > 0 else None

    def _best_opencorporates_company(
        self,
        companies: List[Dict[str, Any]],
        company_name: str,
        state: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        best = None
        best_score = 0
        for wrapper in companies:
            company = wrapper.get("company", {})
            name = company.get("name") or ""
            score = self._score_name_match(company_name, name)
            jurisdiction = company.get("jurisdiction_code")
            if state and jurisdiction == f"us_{state.lower()}":
                score += 2
            if score > best_score:
                best_score = score
                best = company
        return best if best_score > 0 else None

    def _nominatim_to_data(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        address = candidate.get("address") or {}
        extratags = candidate.get("extratags") or {}
        name = candidate.get("namedetails", {}).get("name") or candidate.get("display_name", "").split(",")[0]

        street_parts = [address.get("house_number"), address.get("road")]
        street_address = " ".join([p for p in street_parts if p])

        return {
            "operating_name": name,
            "description": None,
            "industry": self._map_osm_industry(candidate.get("class"), candidate.get("type")),
            "sub_industry": None,
            "services": [],
            "employee_count": None,
            "employee_range": None,
            "contact_info": {
                "main_phone": extratags.get("phone"),
                "secondary_phone": extratags.get("contact:phone"),
                "fax": extratags.get("fax"),
                "main_email": extratags.get("email"),
                "contact_form_url": extratags.get("contact:website"),
            },
            "headquarters": {
                "address": street_address or address.get("road"),
                "city": address.get("city") or address.get("town") or address.get("village"),
                "state": address.get("state") or address.get("state_code"),
                "postal_code": address.get("postcode"),
            },
            "social_media": {
                "website": extratags.get("website") or extratags.get("contact:website"),
                "linkedin_url": None,
                "facebook_url": None,
                "twitter_url": None,
                "instagram_url": None,
                "youtube_url": None,
            },
            "additional_notes": "Data from OpenStreetMap (Nominatim).",
        }

    def _opencorporates_to_data(self, company: Dict[str, Any], officers: List[Dict[str, Any]]) -> Dict[str, Any]:
        registration = {
            "state": company.get("jurisdiction_code"),
            "registration_number": company.get("company_number"),
            "business_type": company.get("company_type"),
            "registered_agent": None,
            "status": company.get("current_status"),
            "filing_date": company.get("incorporation_date"),
        }

        key_personnel = []
        for officer_wrapper in officers[:10]:
            officer = officer_wrapper.get("officer", {})
            name = officer.get("name")
            position = officer.get("position")
            if name:
                key_personnel.append({
                    "name": name,
                    "title": position,
                    "linkedin_url": None,
                    "email": None,
                    "phone": None,
                })
            if position and "agent" in position.lower() and not registration["registered_agent"]:
                registration["registered_agent"] = name

        return {
            "legal_name": company.get("name"),
            "operating_name": company.get("name"),
            "business_registration": registration,
            "key_personnel": key_personnel,
            "additional_notes": "Data from OpenCorporates.",
        }

    async def enrich_company(
        self,
        company_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Dict[str, Any]:
        result = {
            "success": False,
            "website_url": None,
            "confidence": "low",
            "data": None,
            "sources_searched": [],
            "error": None,
            "source": "public",
        }

        normalized_name, _ = normalize_company_name(company_name)

        nominatim_results = await self._nominatim_search(normalized_name, city, state)
        nominatim_best = self._best_nominatim_candidate(nominatim_results, normalized_name, city, state)
        if nominatim_best:
            result["sources_searched"].append(("nominatim", self.nominatim_url))

        oc_company = None
        oc_officers = []
        oc_results = await self._opencorporates_search(normalized_name, state)
        oc_company = self._best_opencorporates_company(oc_results, normalized_name, state)
        if oc_company:
            result["sources_searched"].append(("opencorporates", self.opencorporates_url))
            jurisdiction = oc_company.get("jurisdiction_code")
            number = oc_company.get("company_number")
            if jurisdiction and number:
                oc_officers = await self._opencorporates_officers(jurisdiction, number)

        if not nominatim_best and not oc_company:
            if settings.OPENAI_API_KEY:
                from src.services.web_enrichment import web_enrichment_service

                web_result = await web_enrichment_service.enrich_company(
                    company_name=normalized_name,
                    city=city,
                    state=state,
                    lite=True,
                )
                return {
                    "success": web_result.get("success", False),
                    "website_url": web_result.get("website_url"),
                    "confidence": web_result.get("confidence", "none"),
                    "data": web_result.get("data"),
                    "sources_searched": web_result.get("sources_searched", []),
                    "error": web_result.get("error"),
                    "source": "web_fallback",
                    "dba_names_found": web_result.get("dba_names_found", []),
                }

            result["error"] = "No public listings found"
            return result

        data: Dict[str, Any] = {
            "is_verified_match": True,
            "match_confidence": "medium",
            "verification_notes": "Matched using public sources",
            "legal_name": None,
            "operating_name": None,
            "dba_names": [],
            "parent_company": None,
            "description": None,
            "industry": None,
            "sub_industry": None,
            "naics_code": None,
            "sic_code": None,
            "services": [],
            "year_founded": None,
            "years_in_business": None,
            "business_registration": {},
            "employee_count": None,
            "employee_range": None,
            "contact_info": {
                "main_phone": None,
                "secondary_phone": None,
                "fax": None,
                "main_email": None,
                "contact_form_url": None,
            },
            "headquarters": {
                "address": None,
                "city": None,
                "state": None,
                "postal_code": None,
            },
            "other_locations": [],
            "social_media": {
                "website": None,
                "linkedin_url": None,
                "facebook_url": None,
                "twitter_url": None,
                "instagram_url": None,
                "youtube_url": None,
            },
            "key_personnel": [],
            "certifications": [],
            "safety_programs": [],
            "union_status": None,
            "additional_notes": None,
        }

        if nominatim_best:
            data.update(self._nominatim_to_data(nominatim_best))

        if oc_company:
            data.update(self._opencorporates_to_data(oc_company, oc_officers))

        data["legal_name"] = data.get("legal_name") or company_name
        data["operating_name"] = data.get("operating_name") or company_name

        website_url = data.get("social_media", {}).get("website")
        result["website_url"] = website_url
        result["data"] = data
        result["success"] = True
        result["confidence"] = "high" if nominatim_best and oc_company else "medium"

        return result


public_enrichment_service = PublicEnrichmentService()
