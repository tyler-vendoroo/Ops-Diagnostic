from pydantic import BaseModel
from typing import Optional
from enum import Enum

class LeadStatus(str, Enum):
    new = "new"
    engaged = "engaged"
    diagnostic_started = "diagnostic_started"
    diagnostic_complete = "diagnostic_complete"
    abandoned = "abandoned"

class LeadCapture(BaseModel):
    name: str
    email: str
    company: str
    phone: Optional[str] = None
    event_source: Optional[str] = None
    pms_platform: Optional[str] = None
    terms_accepted: bool = False
    trial_interest: bool = False
    referral_source: Optional[str] = None
