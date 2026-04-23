from pydantic import BaseModel
from typing import Optional, List

class SurveyResponse(BaseModel):
    # Company basics
    door_count: int
    property_count: Optional[int] = None
    pms_platform: Optional[str] = None
    portfolio_model: Optional[str] = None  # sfr, mfr, mixed
    staff_count: Optional[int] = None

    # Vendor coverage
    vendor_count: Optional[int] = None
    trades_covered: List[str] = []

    # Policies
    has_written_emergency_protocols: Optional[str] = None  # yes/no/unsure
    has_defined_ntes: Optional[str] = None
    ntes_are_tiered: bool = False
    has_defined_slas: Optional[str] = None

    # Operations
    estimated_monthly_wos: Optional[int] = None
    estimated_open_rate: Optional[float] = None
    estimated_response_time: Optional[str] = None
    estimated_completion_time: Optional[str] = None
    after_hours_method: Optional[str] = None

    # Goals
    primary_goal: Optional[str] = None  # scale/optimize/elevate
    pain_points: List[str] = []

    # Cost
    annual_cost_per_staff: Optional[float] = None  # Annual loaded cost per coordinator/tech
