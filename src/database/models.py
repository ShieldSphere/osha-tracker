from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Date,
    Float,
    ForeignKey,
    Enum,
    Text,
    UniqueConstraint,
    Boolean,
)
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    pass


class EnrichmentStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NOT_FOUND = "not_found"


# CRM Enums
class ProspectStatus(str, enum.Enum):
    NEW_LEAD = "new_lead"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    WON = "won"
    LOST = "lost"


class ActivityType(str, enum.Enum):
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    NOTE = "note"
    TASK = "task"


class CallbackStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# EPA Enums
class EPACaseStatus(str, enum.Enum):
    OPEN = "open"
    SETTLEMENT = "settlement"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class EPACaseCategory(str, enum.Enum):
    AFR = "AFR"  # Administrative - Formal
    AIF = "AIF"  # Administrative - Informal
    JDC = "JDC"  # Judicial


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    activity_nr = Column(String(20), unique=True, nullable=False, index=True)

    # Establishment info
    reporting_id = Column(String(20))
    state_flag = Column(String(5))
    estab_name = Column(String(255), nullable=False)
    site_address = Column(String(255))
    site_city = Column(String(100))
    site_state = Column(String(2), index=True)
    site_zip = Column(String(10))

    # Mailing address
    mail_street = Column(String(255))
    mail_city = Column(String(100))
    mail_state = Column(String(2))
    mail_zip = Column(String(10))

    # Inspection details
    open_date = Column(Date, index=True)
    case_mod_date = Column(Date)
    close_conf_date = Column(Date)
    close_case_date = Column(Date)
    sic_code = Column(String(10))
    naics_code = Column(String(10))
    insp_type = Column(String(10))
    insp_scope = Column(String(10))
    why_no_insp = Column(String(10))

    # Owner/Union info
    owner_type = Column(String(50))
    owner_code = Column(String(10))
    union_status = Column(String(10))

    # Industry flags
    safety_manuf = Column(String(5))
    safety_const = Column(String(5))
    safety_marit = Column(String(5))
    health_manuf = Column(String(5))
    health_const = Column(String(5))
    health_marit = Column(String(5))
    migrant = Column(String(5))

    # Additional OSHA fields
    adv_notice = Column(String(10))
    safety_hlth = Column(String(10))
    nr_in_estab = Column(Integer)
    host_est_key = Column(String(50))

    # Penalty info (calculated from violations)
    total_current_penalty = Column(Float, default=0)
    total_initial_penalty = Column(Float, default=0)

    # Enrichment tracking
    enrichment_status = Column(
        Enum(EnrichmentStatus),
        default=EnrichmentStatus.PENDING,
        nullable=False
    )
    enrichment_error = Column(Text)
    enrichment_attempts = Column(Integer, default=0)
    last_enrichment_attempt = Column(DateTime)

    # Violation sync tracking
    last_violation_check = Column(DateTime, nullable=True)
    violation_check_count = Column(Integer, default=0)

    # New violation detection
    new_violations_detected = Column(Boolean, default=False)
    new_violations_count = Column(Integer, default=0)
    new_violations_date = Column(DateTime, nullable=True)

    # OSHA load date (when inspection was published to OSHA database)
    load_dt = Column(DateTime, nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="inspection", uselist=False)
    violations = relationship("Violation", back_populates="inspection")
    prospect = relationship("Prospect", back_populates="inspection", uselist=False)

    # Computed field (not stored in DB)
    violation_count: int = 0


class Violation(Base):
    __tablename__ = "violations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    activity_nr = Column(String(20), ForeignKey("inspections.activity_nr"), nullable=False, index=True)
    citation_id = Column(String(20), nullable=False)
    delete_flag = Column(String(5))

    # Violation details
    standard = Column(String(50))  # OSHA standard violated
    viol_type = Column(String(10))  # S=Serious, W=Willful, R=Repeat, O=Other
    issuance_date = Column(Date, index=True)
    abate_date = Column(Date)  # Abatement date
    abate_complete = Column(String(10))

    # Penalty info
    current_penalty = Column(Float, default=0)
    initial_penalty = Column(Float, default=0)

    # Contest/order dates
    contest_date = Column(Date)
    final_order_date = Column(Date)

    # Additional details
    nr_instances = Column(Integer)
    nr_exposed = Column(Integer)  # Number of employees exposed
    rec = Column(String(10))
    gravity = Column(String(20))
    emphasis = Column(String(50))
    hazcat = Column(String(50))  # Hazard category

    # FTA (Failure to Abate) info
    fta_insp_nr = Column(String(20))
    fta_issuance_date = Column(Date)
    fta_penalty = Column(Float)
    fta_contest_date = Column(Date)
    fta_final_order_date = Column(Date)

    # Hazardous substances
    hazsub1 = Column(String(50))
    hazsub2 = Column(String(50))
    hazsub3 = Column(String(50))
    hazsub4 = Column(String(50))
    hazsub5 = Column(String(50))

    # Load date
    load_dt = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    inspection = relationship("Inspection", back_populates="violations")

    __table_args__ = (
        UniqueConstraint("activity_nr", "citation_id", name="uq_activity_citation"),
    )


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=False)

    # Apollo organization data
    apollo_org_id = Column(String(100))
    name = Column(String(255), nullable=False)
    domain = Column(String(255))
    website = Column(String(500))

    # DBA/Operating name fields (from web enrichment)
    legal_name = Column(String(255))  # Registered legal name
    operating_name = Column(String(255))  # DBA/trade name
    dba_names = Column(Text)  # JSON array of all DBA names
    parent_company = Column(String(255))  # Parent company if subsidiary

    # Enrichment source tracking
    enrichment_source = Column(String(50))  # 'web', 'apollo', 'both', 'manual'
    web_enrichment_data = Column(Text)  # Full JSON from web enrichment (for reference)
    web_enriched_at = Column(DateTime)
    apollo_enriched_at = Column(DateTime)

    # Company details
    industry = Column(String(255))
    sub_industry = Column(String(255))
    employee_count = Column(Integer)
    employee_range = Column(String(50))
    annual_revenue = Column(Float)
    revenue_range = Column(String(50))

    # Contact info
    phone = Column(String(50))
    email = Column(String(255))
    linkedin_url = Column(String(500))
    facebook_url = Column(String(500))
    twitter_url = Column(String(500))
    instagram_url = Column(String(500))
    youtube_url = Column(String(500))

    # Business registration info
    year_founded = Column(Integer)
    registration_state = Column(String(50))
    registration_number = Column(String(100))
    registered_agent = Column(String(255))
    business_type = Column(String(100))  # LLC, Corp, etc.

    # Additional addresses (JSON array)
    other_addresses = Column(Text)  # JSON string of additional locations

    # Description and services
    description = Column(Text)
    services = Column(Text)  # JSON array of services

    # Data quality
    confidence = Column(String(20))  # high, medium, low - enrichment verification confidence

    # Address (from Apollo, may differ from inspection site)
    address = Column(String(255))
    city = Column(String(100))
    state = Column(String(50))
    postal_code = Column(String(20))
    country = Column(String(50))

    # Contact tracking
    contacted = Column(Boolean, default=False)
    contacted_date = Column(DateTime, nullable=True)
    contact_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    inspection = relationship("Inspection", back_populates="company")
    contacts = relationship("Contact", back_populates="company")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    # Apollo person data
    apollo_person_id = Column(String(100))

    # Personal info
    first_name = Column(String(100))
    last_name = Column(String(100))
    full_name = Column(String(200))
    title = Column(String(255))

    # Contact details
    email = Column(String(255))
    email_status = Column(String(50))  # verified, unverified, etc.
    phone = Column(String(50))
    mobile_phone = Column(String(50))

    # Professional info
    linkedin_url = Column(String(500))
    seniority = Column(String(50))  # c_suite, vp, director, manager, etc.
    departments = Column(String(255))  # comma-separated

    # Contact type classification
    contact_type = Column(String(50))  # safety_role, executive, both

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="contacts")

    __table_args__ = (
        UniqueConstraint("company_id", "apollo_person_id", name="uq_company_person"),
    )


# =============================================================================
# CRM MODELS
# =============================================================================

class Prospect(Base):
    """
    CRM Prospect - linked to an OSHA Inspection.
    Tracks sales pipeline status for potential consulting clients.
    """
    __tablename__ = "prospects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), unique=True, nullable=False)

    # Pipeline status
    status = Column(
        Enum(ProspectStatus, values_callable=lambda e: [m.value for m in e], name='prospectstatus'),
        default=ProspectStatus.NEW_LEAD,
        nullable=False
    )
    priority = Column(String(20))  # high, medium, low

    # Business info
    estimated_value = Column(Float)
    notes = Column(Text)

    # Next action tracking
    next_action = Column(String(255))
    next_action_date = Column(Date)

    # Outcome tracking
    lost_reason = Column(String(255))  # If status = LOST
    won_date = Column(Date)  # If status = WON
    won_value = Column(Float)  # Actual value if won

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    inspection = relationship("Inspection", back_populates="prospect")
    activities = relationship("Activity", back_populates="prospect", cascade="all, delete-orphan", order_by="desc(Activity.activity_date)")
    callbacks = relationship("Callback", back_populates="prospect", cascade="all, delete-orphan", order_by="Callback.callback_date")


class Activity(Base):
    """
    CRM Activity - tracks interactions with a prospect.
    Types: call, email, meeting, note, task
    """
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id"), nullable=False)

    # Activity details
    activity_type = Column(
        Enum(ActivityType, values_callable=lambda e: [m.value for m in e], name='activitytype'),
        nullable=False
    )
    subject = Column(String(255))
    description = Column(Text)
    outcome = Column(String(255))  # e.g., "Left voicemail", "Scheduled meeting"

    # Timing
    activity_date = Column(DateTime, default=datetime.utcnow)
    duration_minutes = Column(Integer)  # For calls/meetings

    # Task-specific fields
    task_due_date = Column(Date)
    task_completed = Column(Boolean, default=False)
    task_completed_date = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    prospect = relationship("Prospect", back_populates="activities")


class Callback(Base):
    """
    CRM Callback - scheduled follow-ups and reminders.
    """
    __tablename__ = "callbacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id"), nullable=False)

    # Callback details
    callback_date = Column(DateTime, nullable=False)
    callback_type = Column(String(50))  # call, email, meeting
    notes = Column(Text)

    # Status tracking
    status = Column(
        Enum(CallbackStatus, values_callable=lambda e: [m.value for m in e], name='callbackstatus'),
        default=CallbackStatus.PENDING,
        nullable=False
    )
    completed_at = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    prospect = relationship("Prospect", back_populates="callbacks")


# =============================================================================
# EPA ENFORCEMENT MODELS
# =============================================================================

class EPACase(Base):
    """
    EPA Enforcement Case - from ECHO database.
    Tracks environmental enforcement actions (Clean Air Act, Clean Water Act, RCRA, etc.)
    """
    __tablename__ = "epa_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_number = Column(String(50), unique=True, nullable=False, index=True)
    activity_id = Column(String(50), index=True)  # EPA internal activity ID

    # Case identification
    case_name = Column(String(500))  # Usually defendant/company name
    case_category = Column(String(10))  # AFR, AIF, JDC
    case_category_desc = Column(String(100))
    case_status = Column(String(50))
    case_status_desc = Column(String(100))
    civil_criminal = Column(String(10))  # CI=Civil, CR=Criminal

    # Case lead
    case_lead = Column(String(10))  # E=EPA, S=State
    lead_agency = Column(String(100))
    region = Column(String(10))  # EPA Region 01-10

    # Dates
    date_filed = Column(Date)  # When complaint/order issued
    settlement_date = Column(Date)
    date_lodged = Column(Date)  # When consent decree lodged
    date_closed = Column(Date)

    # Financial data
    fed_penalty = Column(Float, default=0)  # Federal penalty assessed
    state_local_penalty = Column(Float, default=0)
    cost_recovery = Column(Float, default=0)
    compliance_action_cost = Column(Float, default=0)
    sep_cost = Column(Float, default=0)  # Supplemental Environmental Projects

    # Facility/Company info
    primary_naics = Column(String(10))
    primary_sic = Column(String(10))
    facility_name = Column(String(255))
    facility_city = Column(String(100))
    facility_state = Column(String(2), index=True)
    facility_zip = Column(String(10))

    # Environmental laws violated (boolean flags)
    caa_flag = Column(Boolean, default=False)  # Clean Air Act
    cwa_flag = Column(Boolean, default=False)  # Clean Water Act
    rcra_flag = Column(Boolean, default=False)  # Resource Conservation and Recovery Act
    sdwa_flag = Column(Boolean, default=False)  # Safe Drinking Water Act
    cercla_flag = Column(Boolean, default=False)  # Superfund
    epcra_flag = Column(Boolean, default=False)  # Emergency Planning and Community Right-to-Know
    tsca_flag = Column(Boolean, default=False)  # Toxic Substances Control Act
    fifra_flag = Column(Boolean, default=False)  # Federal Insecticide, Fungicide, and Rodenticide Act

    # Primary law
    primary_law = Column(String(50))
    primary_section = Column(String(100))

    # Additional flags
    federal_facility = Column(Boolean, default=False)
    tribal_land = Column(Boolean, default=False)
    multimedia = Column(Boolean, default=False)  # Multiple environmental laws

    # Settlement info
    settlement_count = Column(Integer, default=0)
    enforcement_outcome = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CronRun(Base):
    __tablename__ = "cron_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_name = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)  # running, success, failed
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    finished_at = Column(DateTime, nullable=True)
    details = Column(Text, nullable=True)  # JSON blob with stats
    error = Column(Text, nullable=True)
