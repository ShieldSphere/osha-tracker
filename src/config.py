from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/osha_tracker"

    # DOL OSHA API (get key at https://dataportal.dol.gov/)
    DOL_API_KEY: str = ""

    # Apollo.io API
    APOLLO_API_KEY: str = ""
    APOLLO_API_BASE_URL: str = "https://api.apollo.io/api/v1"

    # OpenAI API (for web enrichment)
    OPENAI_API_KEY: str = ""

    # Jina AI Reader (free tier: 1M tokens/month)
    JINA_READER_URL: str = "https://r.jina.ai/"

    # Scheduler Settings
    # More conservative interval to avoid API rate limits
    FETCH_INTERVAL_HOURS: int = 3
    ENRICHMENT_BATCH_SIZE: int = 10
    MAX_ENRICHMENT_ATTEMPTS: int = 3

    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Target contact titles for Apollo search
    SAFETY_TITLES: List[str] = [
        "Safety Director",
        "Safety Manager",
        "EHS Director",
        "EHS Manager",
        "Environmental Health Safety",
        "Compliance Officer",
        "Compliance Manager",
        "Risk Manager",
        "Health and Safety Manager",
        "HSE Manager",
        "OSHA Compliance",
    ]

    EXECUTIVE_TITLES: List[str] = [
        "Owner",
        "CEO",
        "Chief Executive Officer",
        "President",
        "COO",
        "Chief Operating Officer",
        "VP Operations",
        "Vice President Operations",
        "General Manager",
        "Managing Director",
        "Principal",
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
