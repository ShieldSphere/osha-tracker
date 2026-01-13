"""API endpoints for company enrichment with preview and approval workflow."""
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Body
from pydantic import BaseModel

from src.database.connection import get_db_session
from src.database.models import Inspection, Company, Contact
from src.services.company_normalizer import prepare_for_apollo, normalize_company_name
from src.services.apollo_client import ApolloClient
from src.services.web_enrichment import web_enrichment_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/enrichment", tags=["enrichment"])


# Response Models
class QualityAssessment(BaseModel):
    level: str
    score: int
    issues: List[str]


class LocationInfo(BaseModel):
    city: Optional[str]
    state: Optional[str]
    address: Optional[str]


class EnrichmentPreview(BaseModel):
    inspection_id: int
    activity_nr: str
    original_name: str
    normalized_name: str
    search_variants: List[str]
    normalization_changes: List[str]
    location: LocationInfo
    quality: QualityAssessment
    recommendation: str
    recommendation_reason: str
    existing_company: Optional[dict] = None
    estimated_credits: int = 1


class BatchPreviewResponse(BaseModel):
    total_inspections: int
    previews: List[EnrichmentPreview]
    summary: dict


class WebEnrichmentResult(BaseModel):
    success: bool
    website_url: Optional[str]
    confidence: str
    data: Optional[dict]
    sources_searched: List[tuple]
    error: Optional[str]


class ApolloSearchResult(BaseModel):
    success: bool
    organization: Optional[dict]
    people: Optional[List[dict]]
    error: Optional[str]
    credits_used: int = 0


class EnrichmentConfirmation(BaseModel):
    inspection_id: int
    company_saved: bool
    contacts_saved: int
    company_data: Optional[dict]
    error: Optional[str]


class ConfirmEnrichmentRequest(BaseModel):
    """Request body for confirming enrichment."""
    organization: dict
    contacts: Optional[List[dict]] = None


# Endpoints

@router.get("/preview/{inspection_id}", response_model=EnrichmentPreview)
async def preview_enrichment(inspection_id: int):
    """
    Preview enrichment data for a single inspection.

    Shows normalized company name, data quality assessment, and recommendation
    without making any API calls or spending credits.
    """
    with get_db_session() as db:
        inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
        if not inspection:
            raise HTTPException(status_code=404, detail="Inspection not found")

        # Check if already enriched
        existing_company = db.query(Company).filter(
            Company.inspection_id == inspection_id
        ).first()

        # Prepare enrichment preview
        preview_data = prepare_for_apollo(
            estab_name=inspection.estab_name,
            site_city=inspection.site_city,
            site_state=inspection.site_state,
            site_address=inspection.site_address,
        )

        existing_dict = None
        if existing_company:
            existing_dict = {
                "id": existing_company.id,
                "name": existing_company.name,
                "domain": existing_company.domain,
                "apollo_org_id": existing_company.apollo_org_id,
                "industry": existing_company.industry,
                "employee_count": existing_company.employee_count,
            }

        return EnrichmentPreview(
            inspection_id=inspection.id,
            activity_nr=inspection.activity_nr,
            original_name=preview_data['original_name'],
            normalized_name=preview_data['normalized_name'],
            search_variants=preview_data['search_variants'],
            normalization_changes=preview_data['normalization_changes'],
            location=LocationInfo(**preview_data['location']),
            quality=QualityAssessment(**preview_data['quality']),
            recommendation=preview_data['recommendation'],
            recommendation_reason=preview_data['recommendation_reason'],
            existing_company=existing_dict,
            estimated_credits=1 if not existing_company else 0,
        )


@router.get("/preview/batch", response_model=BatchPreviewResponse)
async def preview_batch_enrichment(
    state: Optional[str] = None,
    min_penalty: Optional[float] = Query(None, ge=0),
    min_quality_score: int = Query(60, ge=0, le=100),
    exclude_enriched: bool = Query(True),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Preview enrichment for multiple inspections matching criteria.

    Useful for planning batch enrichment and estimating credit usage.
    """
    with get_db_session() as db:
        query = db.query(Inspection)

        if state:
            query = query.filter(Inspection.site_state == state.upper())

        if min_penalty is not None:
            query = query.filter(Inspection.total_current_penalty >= min_penalty)

        if exclude_enriched:
            # Subquery to get inspection IDs that already have companies
            enriched_ids = db.query(Company.inspection_id).subquery()
            query = query.filter(~Inspection.id.in_(enriched_ids))

        inspections = query.order_by(Inspection.total_current_penalty.desc()).limit(limit * 2).all()

        previews = []
        for inspection in inspections:
            preview_data = prepare_for_apollo(
                estab_name=inspection.estab_name,
                site_city=inspection.site_city,
                site_state=inspection.site_state,
                site_address=inspection.site_address,
            )

            # Filter by quality score
            if preview_data['quality']['score'] < min_quality_score:
                continue

            previews.append(EnrichmentPreview(
                inspection_id=inspection.id,
                activity_nr=inspection.activity_nr,
                original_name=preview_data['original_name'],
                normalized_name=preview_data['normalized_name'],
                search_variants=preview_data['search_variants'],
                normalization_changes=preview_data['normalization_changes'],
                location=LocationInfo(**preview_data['location']),
                quality=QualityAssessment(**preview_data['quality']),
                recommendation=preview_data['recommendation'],
                recommendation_reason=preview_data['recommendation_reason'],
                existing_company=None,
                estimated_credits=1,
            ))

            if len(previews) >= limit:
                break

        # Build summary
        quality_counts = {'high': 0, 'medium': 0, 'low': 0, 'unusable': 0}
        for p in previews:
            quality_counts[p.quality.level] += 1

        summary = {
            "total_matching": len(previews),
            "estimated_credits": len(previews),
            "by_quality": quality_counts,
            "recommended_count": sum(1 for p in previews if p.recommendation == 'enrich_recommended'),
        }

        return BatchPreviewResponse(
            total_inspections=len(inspections),
            previews=previews,
            summary=summary,
        )


@router.post("/web-enrich/{inspection_id}")
async def run_web_enrichment(inspection_id: int):
    """
    Run free web enrichment for an inspection.

    This searches the web for company info without using Apollo credits.
    Useful for finding domain/website before Apollo search.
    """
    with get_db_session() as db:
        inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
        if not inspection:
            raise HTTPException(status_code=404, detail="Inspection not found")

        # Normalize company name first
        normalized_name, _ = normalize_company_name(inspection.estab_name)

        # Run web enrichment
        result = await web_enrichment_service.enrich_company(
            company_name=normalized_name,
            city=inspection.site_city,
            state=inspection.site_state,
        )

        return {
            "inspection_id": inspection_id,
            "company_name": normalized_name,
            "success": result.get("success", False),
            "website_url": result.get("website_url"),
            "confidence": result.get("confidence", "none"),
            "data": result.get("data"),
            "sources_searched": result.get("sources_searched", []),
            "error": result.get("error"),
        }


@router.post("/apollo-search/{inspection_id}")
async def search_apollo(
    inspection_id: int,
    domain: Optional[str] = None,
    use_normalized_name: bool = True,
):
    """
    Search Apollo for organization and contacts.

    This DOES use Apollo credits. Only call after previewing and confirming.

    Args:
        inspection_id: The inspection to enrich
        domain: Optional domain to search (improves accuracy)
        use_normalized_name: Whether to use normalized company name
    """
    with get_db_session() as db:
        inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
        if not inspection:
            raise HTTPException(status_code=404, detail="Inspection not found")

        # Get search name
        if use_normalized_name:
            search_name, _ = normalize_company_name(inspection.estab_name)
        else:
            search_name = inspection.estab_name

        apollo_client = ApolloClient()

        try:
            # Search for organization
            org = None
            if domain:
                # If we have a domain, use enrichment (more accurate)
                org = await apollo_client.enrich_organization(domain=domain)

            if not org:
                # Fall back to name search
                org = await apollo_client.search_organization(
                    name=search_name,
                    city=inspection.site_city,
                    state=inspection.site_state,
                )

            if not org:
                return {
                    "success": False,
                    "organization": None,
                    "people": None,
                    "error": f"No organization found for '{search_name}'",
                    "credits_used": 1,
                }

            # Search for contacts
            org_domain = org.get("primary_domain") or domain
            contacts = await apollo_client.search_contacts_by_titles(
                organization_name=org.get("name", search_name),
                organization_domain=org_domain,
            )

            # Parse organization data
            parsed_org = apollo_client.parse_organization(org)

            # Parse contacts
            safety_contacts = [
                apollo_client.parse_person(p, "safety")
                for p in contacts.get("safety_contacts", [])
            ]
            executive_contacts = [
                apollo_client.parse_person(p, "executive")
                for p in contacts.get("executive_contacts", [])
            ]

            return {
                "success": True,
                "organization": parsed_org,
                "people": {
                    "safety_contacts": safety_contacts,
                    "executive_contacts": executive_contacts,
                },
                "error": None,
                "credits_used": 2 if contacts else 1,  # 1 for org search, 1 for people
            }

        except Exception as e:
            logger.error(f"Apollo search error for inspection {inspection_id}: {e}")
            return {
                "success": False,
                "organization": None,
                "people": None,
                "error": str(e),
                "credits_used": 1,
            }


@router.post("/confirm/{inspection_id}", response_model=EnrichmentConfirmation)
async def confirm_enrichment(
    inspection_id: int,
    request: ConfirmEnrichmentRequest,
):
    """
    Confirm and save enrichment data to database.

    Call this after reviewing Apollo search results to save the data.
    """
    organization = request.organization
    contacts = request.contacts

    with get_db_session() as db:
        inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
        if not inspection:
            raise HTTPException(status_code=404, detail="Inspection not found")

        try:
            # Check if company already exists
            existing_company = db.query(Company).filter(
                Company.inspection_id == inspection_id
            ).first()

            if existing_company:
                # Update existing company
                for key, value in organization.items():
                    if hasattr(existing_company, key) and value is not None:
                        setattr(existing_company, key, value)
                existing_company.updated_at = datetime.utcnow()
                company = existing_company
            else:
                # Create new company
                company = Company(
                    inspection_id=inspection_id,
                    **{k: v for k, v in organization.items() if hasattr(Company, k)}
                )
                db.add(company)
                db.flush()  # Get the ID

            # Save contacts
            contacts_saved = 0
            if contacts:
                for contact_data in contacts:
                    # Check if contact already exists
                    existing_contact = None
                    if contact_data.get("apollo_person_id"):
                        existing_contact = db.query(Contact).filter(
                            Contact.company_id == company.id,
                            Contact.apollo_person_id == contact_data["apollo_person_id"]
                        ).first()

                    if existing_contact:
                        # Update existing contact
                        for key, value in contact_data.items():
                            if hasattr(existing_contact, key) and value is not None:
                                setattr(existing_contact, key, value)
                    else:
                        # Create new contact
                        contact = Contact(
                            company_id=company.id,
                            **{k: v for k, v in contact_data.items() if hasattr(Contact, k)}
                        )
                        db.add(contact)
                        contacts_saved += 1

            db.commit()

            return EnrichmentConfirmation(
                inspection_id=inspection_id,
                company_saved=True,
                contacts_saved=contacts_saved,
                company_data={
                    "id": company.id,
                    "name": company.name,
                    "domain": company.domain,
                    "apollo_org_id": company.apollo_org_id,
                },
                error=None,
            )

        except Exception as e:
            db.rollback()
            logger.error(f"Error saving enrichment for inspection {inspection_id}: {e}")
            return EnrichmentConfirmation(
                inspection_id=inspection_id,
                company_saved=False,
                contacts_saved=0,
                company_data=None,
                error=str(e),
            )


class RevealContactsRequest(BaseModel):
    """Request body for revealing contact info."""
    person_ids: List[str]


@router.post("/reveal-contacts")
async def reveal_contacts(request: RevealContactsRequest):
    """
    Reveal email and phone for selected contacts (uses Apollo credits).

    This is Step 2 of the enrichment process - only called for contacts
    the user explicitly selects to reveal.
    """
    if not request.person_ids:
        return {
            "success": False,
            "contacts": [],
            "error": "No person IDs provided",
            "credits_used": 0,
        }

    apollo_client = ApolloClient()

    try:
        revealed = []
        credits_used = 0

        for person_id in request.person_ids:
            try:
                person = await apollo_client.reveal_contact_info(person_id)
                if person:
                    # Determine contact type based on title
                    title = (person.get("title") or "").lower()
                    safety_keywords = ["safety", "ehs", "compliance", "risk", "health"]
                    contact_type = "safety" if any(kw in title for kw in safety_keywords) else "executive"

                    revealed.append(apollo_client.parse_person(person, contact_type))
                    credits_used += 1
            except Exception as e:
                logger.error(f"Failed to reveal contact {person_id}: {e}")
                # Continue with other contacts

        return {
            "success": True,
            "contacts": revealed,
            "error": None,
            "credits_used": credits_used,
        }

    except Exception as e:
        logger.error(f"Error revealing contacts: {e}")
        return {
            "success": False,
            "contacts": [],
            "error": str(e),
            "credits_used": 0,
        }


@router.get("/stats")
async def get_enrichment_stats():
    """Get statistics about enrichment status."""
    with get_db_session() as db:
        total_inspections = db.query(Inspection).count()
        enriched_count = db.query(Company).count()
        contact_count = db.query(Contact).count()

        # Quality distribution of unenriched inspections
        from sqlalchemy import func
        unenriched = db.query(Inspection).filter(
            ~Inspection.id.in_(db.query(Company.inspection_id))
        ).limit(1000).all()

        quality_dist = {'high': 0, 'medium': 0, 'low': 0, 'unusable': 0}
        for insp in unenriched:
            preview = prepare_for_apollo(
                insp.estab_name, insp.site_city, insp.site_state, insp.site_address
            )
            quality_dist[preview['quality']['level']] += 1

        return {
            "total_inspections": total_inspections,
            "enriched_inspections": enriched_count,
            "unenriched_inspections": total_inspections - enriched_count,
            "total_contacts": contact_count,
            "enrichment_rate": round(enriched_count / total_inspections * 100, 1) if total_inspections > 0 else 0,
            "unenriched_quality_distribution": quality_dist,
        }
