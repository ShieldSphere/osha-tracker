"""Web enrichment service using multi-source search, Jina Reader and OpenAI."""
import logging
import httpx
import json
import re
from typing import Optional, Dict, Any, List
from urllib.parse import quote_plus, unquote

from openai import OpenAI

from src.config import settings

logger = logging.getLogger(__name__)


class WebEnrichmentService:
    """Service to enrich company data from multiple web sources."""

    def __init__(self):
        self.openai_client = None
        if settings.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

    async def _duckduckgo_search(self, query: str, num_results: int = 10) -> List[str]:
        """Search DuckDuckGo and return list of URLs."""
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                response.raise_for_status()

            # Extract URLs from search results
            urls = re.findall(r'href="//duckduckgo\.com/l/\?uddg=([^"&]+)', response.text)
            decoded_urls = [unquote(u) for u in urls[:num_results]]
            cleaned_urls = []
            for url in decoded_urls:
                if "duckduckgo.com/" in url:
                    continue
                if "bing.com/aclick" in url:
                    continue
                cleaned_urls.append(url)
            return cleaned_urls
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []

    async def _fetch_with_jina(self, url: str, max_chars: int = 15000) -> Optional[str]:
        """Fetch URL content using Jina Reader."""
        if not url:
            return None

        jina_url = f"{settings.JINA_READER_URL}{url}"
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(jina_url, headers={"Accept": "text/markdown"})
                response.raise_for_status()

            content = response.text
            if len(content) > max_chars:
                content = content[:max_chars] + "\n\n[Content truncated...]"
            return content
        except Exception as e:
            logger.error(f"Jina fetch error for {url}: {e}")
            return None

    async def search_company_website(self, company_name: str, city: str = None, state: str = None) -> Optional[str]:
        """Find the company's main website."""
        search_query = f"{company_name}"
        if city:
            search_query += f" {city}"
        if state:
            search_query += f" {state}"

        logger.info(f"Searching for company website: {search_query}")
        urls = await self._duckduckgo_search(search_query)

        # Filter out social media and directory sites to find main company website
        skip_domains = [
            'linkedin.com', 'facebook.com', 'twitter.com', 'instagram.com',
            'yelp.com', 'bbb.org', 'yellowpages.com', 'manta.com', 'dnb.com',
            'indeed.com', 'glassdoor.com', 'wikipedia.org', 'bloomberg.com',
            'zoominfo.com', 'mapquest.com', 'google.com', 'bing.com'
        ]

        for url in urls:
            if not any(skip in url.lower() for skip in skip_domains):
                logger.info(f"Found company website: {url}")
                return url

        return None

    async def find_dba_names(self, company_name: str, city: str = None, state: str = None) -> List[str]:
        """
        Search for DBA (Doing Business As) names, parent companies, and trade names.
        This helps find companies that operate under different names than their legal name.
        """
        dba_names = []

        # Search queries specifically for DBA/parent company info
        search_queries = [
            f'"{company_name}" "doing business as"',
            f'"{company_name}" "also known as"',
            f'"{company_name}" "dba"',
            f'"{company_name}" "parent company"',
            f'"{company_name}" "subsidiary of"',
            f'"{company_name}" "owned by"',
        ]

        if state:
            search_queries.append(f'"{company_name}" {state} business registration')

        all_urls = []
        for query in search_queries[:3]:  # Limit to avoid too many requests
            urls = await self._duckduckgo_search(query, num_results=3)
            all_urls.extend(urls)

        # Fetch content and use OpenAI to extract DBA names
        if all_urls and self.openai_client:
            # Get first relevant result
            content_pieces = []
            for url in all_urls[:2]:
                content = await self._fetch_with_jina(url, max_chars=5000)
                if content:
                    content_pieces.append(content)

            if content_pieces:
                combined = "\n\n---\n\n".join(content_pieces)
                dba_prompt = f"""Analyze the following web content about "{company_name}".

Your task: Find any alternate names this company operates under.

Look for:
1. "Doing Business As" (DBA) names
2. Trade names or brand names
3. Parent company names (if this is a subsidiary)
4. Former company names
5. Any other names the company is known by

Return ONLY a JSON array of alternate names found. If none found, return empty array.
Example: ["Ole Mexican Foods", "Good Harvest LLC"]

IMPORTANT:
- Only include names that are clearly associated with "{company_name}"
- Do NOT include unrelated company names
- Do NOT make up names - only include what's explicitly mentioned
- Return just the JSON array, no other text

Content:
{combined}"""

                try:
                    response = self.openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You extract company names from text. Return only valid JSON arrays."},
                            {"role": "user", "content": dba_prompt}
                        ],
                        temperature=0.1,
                        max_tokens=500
                    )
                    result_text = response.choices[0].message.content.strip()

                    # Clean up response
                    if result_text.startswith("```"):
                        result_text = result_text.split("```")[1]
                        if result_text.startswith("json"):
                            result_text = result_text[4:]
                    result_text = result_text.strip()

                    names = json.loads(result_text)
                    if isinstance(names, list):
                        dba_names = [n for n in names if n and isinstance(n, str)]
                        logger.info(f"Found DBA names for {company_name}: {dba_names}")
                except Exception as e:
                    logger.error(f"Error finding DBA names: {e}")

        return dba_names

    async def search_linkedin_profile(self, company_name: str, state: str = None) -> Optional[str]:
        """Find company's LinkedIn page."""
        query = f"site:linkedin.com/company {company_name}"
        if state:
            query += f" {state}"

        urls = await self._duckduckgo_search(query, num_results=5)
        for url in urls:
            if 'linkedin.com/company' in url.lower():
                logger.info(f"Found LinkedIn: {url}")
                return url
        return None

    async def search_facebook_page(self, company_name: str, state: str = None) -> Optional[str]:
        """Find company's Facebook page."""
        query = f"site:facebook.com {company_name}"
        if state:
            query += f" {state}"

        urls = await self._duckduckgo_search(query, num_results=5)
        for url in urls:
            if 'facebook.com' in url.lower() and '/posts/' not in url.lower():
                logger.info(f"Found Facebook: {url}")
                return url
        return None

    async def search_secretary_of_state(self, company_name: str, state: str) -> Optional[str]:
        """Search for Secretary of State business registration."""
        if not state:
            return None

        # Map state abbreviations to full names for better search
        state_names = {
            'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
            'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
            'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
            'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
            'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
            'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
            'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
            'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
            'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
            'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
            'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
            'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
            'WI': 'Wisconsin', 'WY': 'Wyoming'
        }

        state_full = state_names.get(state.upper(), state)
        query = f"{company_name} {state_full} secretary of state business registration"
        urls = await self._duckduckgo_search(query, num_results=5)

        # Look for state government sites
        for url in urls:
            if '.gov' in url.lower() or 'sos.' in url.lower() or 'secretary' in url.lower():
                logger.info(f"Found SOS record: {url}")
                return url
        return None

    async def search_leadership_contacts(self, company_name: str, state: str = None) -> List[str]:
        """Search for company leadership and contact pages."""
        queries = [
            f"{company_name} leadership team",
            f"{company_name} about us management",
            f"{company_name} contact owner CEO",
            f"site:linkedin.com/in {company_name} owner CEO president"
        ]
        if state:
            queries = [f"{q} {state}" for q in queries]

        all_urls = []
        for query in queries:
            urls = await self._duckduckgo_search(query, num_results=5)
            all_urls.extend(urls)

        # Deduplicate while preserving order
        seen = set()
        unique_urls = []
        for url in all_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        return unique_urls[:10]

    def _extract_with_openai(self, content: str, prompt: str, max_tokens: int = 2000) -> Optional[Dict]:
        """Use OpenAI to extract structured data from content."""
        if not self.openai_client or not content:
            return None

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a data extraction assistant. Extract information and return valid JSON only. Be accurate - only include information explicitly found in the content. Use null for missing data."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=max_tokens
            )

            result_text = response.choices[0].message.content.strip()

            # Clean up markdown code blocks
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

            return json.loads(result_text.strip())
        except Exception as e:
            logger.error(f"OpenAI extraction error: {e}")
            return None

    async def enrich_company(self, company_name: str, city: str = None, state: str = None, lite: bool = False) -> Dict[str, Any]:
        """
        Full multi-source enrichment pipeline.

        Searches:
        0. DBA/alternate name search - find if company operates under different name
        1. Company website - for basic info, services, contact
        2. LinkedIn company page - for company details, employee count
        3. Facebook page - for social presence, reviews
        4. Secretary of State - for business registration, founding date
        5. Leadership/contact searches - for key personnel with LinkedIn profiles
        """
        result = {
            "success": False,
            "website_url": None,
            "data": None,
            "error": None,
            "sources_searched": [],
            "confidence": "low",
            "dba_names_found": []
        }

        all_content = []
        has_verified_source = False  # Track if we have a high-confidence source
        search_names = [company_name]  # Names to search for

        logger.info(f"Starting enrichment for: {company_name}, {city}, {state} (lite={lite})")

        # 0. First, search for DBA/alternate names (skip in lite mode)
        if not lite:
            dba_names = await self.find_dba_names(company_name, city, state)
            if dba_names:
                result["dba_names_found"] = dba_names
                search_names.extend(dba_names)
                logger.info(f"Will also search for DBA names: {dba_names}")

        # 1. Find and fetch company website (try original name first, then DBAs)
        website_url = None
        for name in search_names:
            website_url = await self.search_company_website(name, city, state)
            if website_url:
                logger.info(f"Found website using name '{name}': {website_url}")
                break

        if website_url:
            result["website_url"] = website_url
            result["sources_searched"].append(("website", website_url))
            content = await self._fetch_with_jina(website_url, max_chars=12000)
            if content:
                all_content.append(f"=== COMPANY WEBSITE ({website_url}) ===\n{content}")
                has_verified_source = True

        # 2. Find LinkedIn company page (try all names)
        linkedin_url = None
        for name in search_names:
            linkedin_url = await self.search_linkedin_profile(name, state)
            if linkedin_url:
                break
        if linkedin_url:
            result["sources_searched"].append(("linkedin", linkedin_url))
            content = await self._fetch_with_jina(linkedin_url, max_chars=8000)
            if content:
                all_content.append(f"=== LINKEDIN PAGE ({linkedin_url}) ===\n{content}")

        # 3. Find Facebook page
        facebook_url = await self.search_facebook_page(company_name, state)
        if facebook_url:
            result["sources_searched"].append(("facebook", facebook_url))
            content = await self._fetch_with_jina(facebook_url, max_chars=5000)
            if content:
                all_content.append(f"=== FACEBOOK PAGE ({facebook_url}) ===\n{content}")

        # 4. Search Secretary of State records
        sos_url = await self.search_secretary_of_state(company_name, state) if not lite else None
        if sos_url:
            result["sources_searched"].append(("secretary_of_state", sos_url))
            content = await self._fetch_with_jina(sos_url, max_chars=5000)
            if content:
                all_content.append(f"=== SECRETARY OF STATE ({sos_url}) ===\n{content}")
                has_verified_source = True  # SOS records are authoritative

        # 5. Search for leadership/contacts - only if we have verified sources
        if has_verified_source and not lite:
            leadership_urls = await self.search_leadership_contacts(company_name, state)
            for url in leadership_urls[:3]:  # Limit to top 3 to save tokens
                result["sources_searched"].append(("leadership_search", url))
                content = await self._fetch_with_jina(url, max_chars=5000)
                if content:
                    all_content.append(f"=== LEADERSHIP/CONTACT PAGE ({url}) ===\n{content}")

        if not all_content:
            result["error"] = "Could not fetch content from any sources"
            return result

        # Combine all content for extraction
        combined_content = "\n\n".join(all_content)

        # Truncate if too long (GPT-4o-mini context limit considerations)
        max_total = 50000
        if len(combined_content) > max_total:
            combined_content = combined_content[:max_total] + "\n\n[Content truncated...]"

        logger.info(f"Extracting data from {len(all_content)} sources ({len(combined_content)} chars)")

        # Build location context for verification
        location_context = ""
        if city and state:
            location_context = f"in or near {city}, {state}"
        elif state:
            location_context = f"in {state}"
        elif city:
            location_context = f"in or near {city}"

        # Include DBA names found in prompt context
        dba_context = ""
        if result.get("dba_names_found"):
            dba_context = f"\nKNOWN ALTERNATE NAMES: {', '.join(result['dba_names_found'])}"

        # Extract comprehensive company data with VERIFICATION
        extraction_prompt = f"""You are a business intelligence analyst extracting company data from web sources.

TARGET COMPANY: "{company_name}"
EXPECTED LOCATION: {location_context if location_context else "unknown"}{dba_context}

CRITICAL: UNDERSTANDING DBA (DOING BUSINESS AS) RELATIONSHIPS
Many companies operate under names DIFFERENT from their legal/registered name:
- "GOOD HARVEST GRAINS" might do business as "Ole Mexican Foods"
- A legal entity name like "ABC Holdings LLC" might operate stores as "Joe's Pizza"
- Parent companies often own subsidiaries with completely different names

Your verification should consider:
1. The company might be found under a DBA/trade name, not its legal name
2. The location MUST match (same city/state or very close)
3. Industry/business type should be consistent
4. Look for phrases like "doing business as", "d/b/a", "operating as", "also known as"

If you find content about the company under a DIFFERENT operating name but at the CORRECT location, this IS a verified match - just note the relationship.

Extract information into this JSON structure:

{{
    "is_verified_match": true,
    "match_confidence": "high/medium/low",
    "verification_notes": "Explain the company name relationship (e.g., 'Found as DBA Ole Mexican Foods')",

    "legal_name": "The registered/legal company name (from OSHA: {company_name})",
    "operating_name": "The name the company actually operates under (brand/DBA name)",
    "dba_names": ["All 'doing business as' or trade names found"],
    "parent_company": "Parent company name if this is a subsidiary",

    "description": "What the company does (2-3 sentences)",

    "industry": "Primary industry category",
    "sub_industry": "More specific industry",
    "naics_code": "NAICS code if found",
    "sic_code": "SIC code if found",
    "services": ["List of services/products offered"],

    "year_founded": 2000,
    "years_in_business": 24,

    "business_registration": {{
        "state": "State where registered",
        "registration_number": "Business ID/filing number",
        "business_type": "LLC, Corporation, etc.",
        "registered_agent": "Name of registered agent",
        "status": "Active, Inactive, etc.",
        "filing_date": "Original filing date"
    }},

    "employee_count": 50,
    "employee_range": "11-50 employees",

    "contact_info": {{
        "main_phone": "Primary phone number",
        "secondary_phone": "Secondary phone if available",
        "fax": "Fax number if available",
        "main_email": "Primary contact email",
        "contact_form_url": "URL to contact form if no email"
    }},

    "headquarters": {{
        "address": "Street address",
        "city": "City",
        "state": "State",
        "postal_code": "ZIP code"
    }},

    "other_locations": [
        {{"address": "Full address", "type": "Branch/Office/Warehouse/Plant"}}
    ],

    "social_media": {{
        "website": "Main company website URL",
        "linkedin_url": "LinkedIn company page URL",
        "facebook_url": "Facebook page URL",
        "twitter_url": "Twitter/X URL",
        "instagram_url": "Instagram URL",
        "youtube_url": "YouTube channel URL"
    }},

    "key_personnel": [
        {{
            "name": "Full name",
            "title": "Job title (Owner, CEO, President, Safety Director, etc.)",
            "linkedin_url": "Their personal LinkedIn profile URL if found",
            "email": "Their email if found",
            "phone": "Their direct phone if found"
        }}
    ],

    "certifications": ["Any safety, quality, industry certifications"],
    "safety_programs": ["Any mentioned safety initiatives or programs"],
    "union_status": "Union or non-union if mentioned",

    "additional_notes": "Any other relevant business information found"
}}

IMPORTANT INSTRUCTIONS:
- VERIFY this is the correct company before extracting data
- If sources show conflicting companies, only extract from verified matching sources
- Set "is_verified_match" to false if you cannot confirm this is the target company
- Set "match_confidence" to "low" if only social media without clear location match
- Use null for any field where information is not found
- NEVER make up or guess information - only include what's explicitly in the content
- If the company name in the content is significantly different, this is likely the WRONG company

Content from multiple sources:
{combined_content}
"""

        extracted_data = self._extract_with_openai(combined_content, extraction_prompt, max_tokens=3000)

        if not extracted_data:
            result["error"] = "Could not extract company data"
            return result

        # Check verification status
        is_verified = extracted_data.get("is_verified_match", False)
        match_confidence = extracted_data.get("match_confidence", "low")

        if not is_verified:
            result["error"] = f"Could not verify this data matches {company_name}. {extracted_data.get('verification_notes', '')}"
            result["confidence"] = "none"
            logger.warning(f"Enrichment failed verification for {company_name}: {extracted_data.get('verification_notes', '')}")
            return result

        # Set confidence based on sources and AI confidence
        if has_verified_source and match_confidence == "high":
            result["confidence"] = "high"
        elif has_verified_source or match_confidence in ["high", "medium"]:
            result["confidence"] = "medium"
        else:
            result["confidence"] = "low"

        # Add the URLs we found directly
        if linkedin_url and extracted_data.get("social_media"):
            extracted_data["social_media"]["linkedin_url"] = linkedin_url
        if facebook_url and extracted_data.get("social_media"):
            extracted_data["social_media"]["facebook_url"] = facebook_url

        result["success"] = True
        result["data"] = extracted_data
        logger.info(f"Successfully enriched {company_name} (confidence: {result['confidence']}) with data from {len(result['sources_searched'])} sources")

        return result


# Singleton instance
web_enrichment_service = WebEnrichmentService()
