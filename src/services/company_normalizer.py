"""Utility to normalize and clean company names from OSHA data."""
import re
from typing import Tuple, List, Optional


# Common suffixes to normalize
COMPANY_SUFFIXES = [
    r'\bINC\.?$', r'\bINCORPORATED$', r'\bCORP\.?$', r'\bCORPORATION$',
    r'\bLLC\.?$', r'\bL\.?L\.?C\.?$', r'\bLTD\.?$', r'\bLIMITED$',
    r'\bCO\.?$', r'\bCOMPANY$', r'\bLP\.?$', r'\bL\.?P\.?$',
    r'\bLLP\.?$', r'\bL\.?L\.?P\.?$', r'\bPC\.?$', r'\bP\.?C\.?$',
    r'\bPLC\.?$', r'\bP\.?L\.?C\.?$', r'\bNA\.?$', r'\bN\.?A\.?$',
]

# Words that suggest poor data quality
LOW_QUALITY_INDICATORS = [
    'unknown', 'n/a', 'none', 'test', 'sample', 'example',
    'do not use', 'deleted', 'duplicate', 'temp', 'temporary',
]

# Common abbreviations to expand
ABBREVIATIONS = {
    'INTL': 'INTERNATIONAL',
    'NATL': 'NATIONAL',
    'SVCS': 'SERVICES',
    'SVC': 'SERVICE',
    'MGMT': 'MANAGEMENT',
    'MFNG': 'MANUFACTURING',
    'MFG': 'MANUFACTURING',
    'CONSTR': 'CONSTRUCTION',
    'CONST': 'CONSTRUCTION',
    'CONTRS': 'CONTRACTORS',
    'CONTR': 'CONTRACTOR',
    'EQUIP': 'EQUIPMENT',
    'ELEC': 'ELECTRIC',
    'ELECTR': 'ELECTRICAL',
    'MECH': 'MECHANICAL',
    'INDUS': 'INDUSTRIES',
    'IND': 'INDUSTRIES',
    'ASSOC': 'ASSOCIATES',
    'BROS': 'BROTHERS',
    'CTR': 'CENTER',
    'DEPT': 'DEPARTMENT',
    'DIST': 'DISTRIBUTION',
    'DIV': 'DIVISION',
    'GRP': 'GROUP',
    'HOSP': 'HOSPITAL',
    'MTN': 'MOUNTAIN',
    'PKG': 'PACKAGING',
    'PLBG': 'PLUMBING',
    'PROP': 'PROPERTIES',
    'PROPS': 'PROPERTIES',
    'SYS': 'SYSTEMS',
    'TECH': 'TECHNOLOGY',
    'TECHS': 'TECHNOLOGIES',
    'TRANSP': 'TRANSPORTATION',
    'TRANS': 'TRANSPORTATION',
    'WHSE': 'WAREHOUSE',
}


def normalize_company_name(name: str) -> Tuple[str, List[str]]:
    """
    Normalize a company name for better search matching.

    Returns:
        Tuple of (normalized_name, list_of_changes_made)
    """
    if not name:
        return "", ["Empty name"]

    changes = []
    original = name

    # Convert to uppercase for processing
    name = name.upper().strip()

    # Remove extra whitespace
    name = re.sub(r'\s+', ' ', name)
    if name != original.upper().strip():
        changes.append("Cleaned whitespace")

    # Remove special characters but keep essential punctuation
    cleaned = re.sub(r'[^\w\s\-\&\.\']', '', name)
    if cleaned != name:
        changes.append("Removed special characters")
        name = cleaned

    # Expand common abbreviations
    words = name.split()
    expanded_words = []
    for word in words:
        if word in ABBREVIATIONS:
            expanded_words.append(ABBREVIATIONS[word])
            changes.append(f"Expanded '{word}' to '{ABBREVIATIONS[word]}'")
        else:
            expanded_words.append(word)
    name = ' '.join(expanded_words)

    # Convert to title case for readability
    name = name.title()

    # Fix common title case issues (LLC, INC, etc. should stay uppercase)
    name = re.sub(r'\bLlc\b', 'LLC', name)
    name = re.sub(r'\bInc\b', 'Inc.', name)
    name = re.sub(r'\bCorp\b', 'Corp.', name)
    name = re.sub(r'\bLtd\b', 'Ltd.', name)
    name = re.sub(r'\bLp\b', 'LP', name)
    name = re.sub(r'\bLlp\b', 'LLP', name)
    name = re.sub(r'\b&\b', '&', name)

    if name != original:
        changes.append("Converted to title case")

    return name.strip(), changes


def get_search_variants(name: str) -> List[str]:
    """
    Generate search variants for a company name.

    Returns multiple versions to try for better matching.
    """
    variants = [name]

    # Version without suffix
    for suffix_pattern in COMPANY_SUFFIXES:
        no_suffix = re.sub(suffix_pattern, '', name, flags=re.IGNORECASE).strip()
        if no_suffix != name and no_suffix and len(no_suffix) > 3:
            variants.append(no_suffix)
            break  # Only remove one suffix

    # Version with "The" removed from start
    if name.lower().startswith('the '):
        variants.append(name[4:])

    # Remove duplicates while preserving order
    seen = set()
    unique_variants = []
    for v in variants:
        v_lower = v.lower()
        if v_lower not in seen:
            seen.add(v_lower)
            unique_variants.append(v)

    return unique_variants


def assess_data_quality(
    estab_name: str,
    site_city: Optional[str] = None,
    site_state: Optional[str] = None,
    site_address: Optional[str] = None,
) -> Tuple[str, List[str], int]:
    """
    Assess the quality of OSHA establishment data for enrichment.

    Returns:
        Tuple of (quality_level, issues_list, quality_score)
        quality_level: 'high', 'medium', 'low', 'unusable'
        quality_score: 0-100
    """
    issues = []
    score = 100

    # Check company name
    if not estab_name or len(estab_name.strip()) < 3:
        issues.append("Company name is missing or too short")
        score -= 50
    else:
        name_lower = estab_name.lower().strip()

        # Check for low quality indicators
        if any(indicator in name_lower for indicator in LOW_QUALITY_INDICATORS):
            issues.append("Company name contains low-quality indicator")
            score -= 40

        # Check for all numbers (likely an ID, not a name)
        if re.match(r'^[\d\s\-]+$', estab_name):
            issues.append("Company name appears to be an ID number")
            score -= 50

        # Check for very short names (likely abbreviations)
        if len(estab_name.strip()) < 5:
            issues.append("Company name is very short")
            score -= 20

        # Check for all caps (common in OSHA data, slightly lower quality)
        if estab_name.isupper() and len(estab_name) > 10:
            issues.append("Company name is all uppercase (may need normalization)")
            score -= 5

        # Check for generic names
        generic_names = ['construction', 'services', 'company', 'contractor', 'industries']
        if name_lower in generic_names:
            issues.append("Company name is too generic")
            score -= 30

    # Check location data
    if not site_state:
        issues.append("State is missing")
        score -= 15

    if not site_city:
        issues.append("City is missing")
        score -= 10

    if not site_address:
        issues.append("Address is missing")
        score -= 5

    # Determine quality level
    if score >= 80:
        quality_level = 'high'
    elif score >= 60:
        quality_level = 'medium'
    elif score >= 40:
        quality_level = 'low'
    else:
        quality_level = 'unusable'

    return quality_level, issues, max(0, score)


def prepare_for_apollo(
    estab_name: str,
    site_city: Optional[str] = None,
    site_state: Optional[str] = None,
    site_address: Optional[str] = None,
) -> dict:
    """
    Prepare OSHA establishment data for Apollo search.

    Returns a dict with:
        - normalized_name: Cleaned company name
        - search_variants: Alternative names to try
        - quality: Data quality assessment
        - recommendation: Whether to proceed with Apollo
        - warnings: Any issues to be aware of
    """
    # Normalize the name
    normalized_name, normalization_changes = normalize_company_name(estab_name)

    # Get search variants
    search_variants = get_search_variants(normalized_name)

    # Assess data quality
    quality_level, issues, quality_score = assess_data_quality(
        estab_name, site_city, site_state, site_address
    )

    # Build recommendation
    if quality_level == 'unusable':
        recommendation = 'do_not_enrich'
        recommendation_reason = "Data quality too low - would likely waste Apollo credits"
    elif quality_level == 'low':
        recommendation = 'enrich_with_caution'
        recommendation_reason = "Data quality is low - verify results carefully"
    elif quality_level == 'medium':
        recommendation = 'enrich_recommended'
        recommendation_reason = "Data quality acceptable - should get reasonable results"
    else:
        recommendation = 'enrich_recommended'
        recommendation_reason = "Data quality is good - likely to find accurate match"

    return {
        'original_name': estab_name,
        'normalized_name': normalized_name,
        'search_variants': search_variants,
        'normalization_changes': normalization_changes,
        'location': {
            'city': site_city,
            'state': site_state,
            'address': site_address,
        },
        'quality': {
            'level': quality_level,
            'score': quality_score,
            'issues': issues,
        },
        'recommendation': recommendation,
        'recommendation_reason': recommendation_reason,
    }
