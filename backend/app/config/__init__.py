from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/vendoroo_diagnostics"
    resend_api_key: str = ""
    diagnostic_from_email: str = "diagnostics@vendoroo.ai"
    sales_notification_email: str = "sales@vendoroo.ai"
    revenue_hero_api_key: str = ""
    revenue_hero_webhook_url: str = ""
    frontend_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    event_source: str = "web"
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "https://ops-diagnostic.vercel.app",
        "https://vendoroo.ai",
    ]

    class Config:
        env_file = ".env"

settings = Settings()

# ── Domain constants (migrated from config/settings.py) ──────────────────────

CORE_TRADES = [
    "plumbing", "electrical", "rooter", "appliance repair",
    "handyperson", "hvac", "roofing", "pest control",
]

SPECIALTY_TRADES = [
    "painting", "flooring", "landscaping", "pool/spa",
    "locksmith", "cleaning/turnover",
]

ALL_TRADES = CORE_TRADES + SPECIALTY_TRADES

REQUIRED_TRADES = CORE_TRADES

DEFAULT_CATEGORY_WEIGHTS = {
    "policy_completeness": 0.125,
    "vendor_coverage": 0.125,
    "response_efficiency": 0.125,
    "documentation_quality": 0.125,
    "operational_consistency": 0.125,
    "after_hours_readiness": 0.125,
    "emergency_protocols": 0.125,
    "scalability_potential": 0.125,
}
