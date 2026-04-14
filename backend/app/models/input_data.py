"""Pydantic models for parsed input data from CSV/Excel files."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class WorkOrder(BaseModel):
    """A single work order record from PMS export."""
    work_order_id: str
    created_date: datetime
    completed_date: Optional[datetime] = None
    status: str  # open, closed, completed, in_progress, etc.
    category: Optional[str] = None  # plumbing, electrical, hvac, etc.
    description: Optional[str] = None
    vendor_name: Optional[str] = None
    cost: Optional[float] = None
    priority: Optional[str] = None  # emergency, urgent, normal, low
    property_name: Optional[str] = None
    unit: Optional[str] = None


class Vendor(BaseModel):
    """A single vendor record from PMS export."""
    vendor_name: str
    trade: Optional[str] = None  # plumbing, electrical, hvac, etc.
    phone: Optional[str] = None
    email: Optional[str] = None
    active: bool = True
    assignment_count: Optional[int] = None  # number of WOs assigned


class Property(BaseModel):
    """A single property record from PMS export."""
    property_name: str
    address: Optional[str] = None
    unit_count: int = 1
    property_type: Optional[str] = None  # residential, commercial, mixed
    occupancy_rate: Optional[float] = None  # 0.0 to 1.0


class ClientInfo(BaseModel):
    """Client information entered by the sales rep."""
    company_name: str
    door_count: int
    property_count: int
    pms_platform: str  # AppFolio, Buildium, RentManager, Other
    operational_model: str  # va, tech
    operational_model_display: str = ""  # "VA (Virtual Assistant Coordinators)"
    staff_count: int = 1  # coordinators or techs
    primary_goal: str = "scale"  # "scale", "optimize", "elevate"
    primary_goal_display: str = "Scale"
    goal_description: str = "Grow portfolio without adding headcount"
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    event_source: Optional[str] = None
    lead_id: Optional[str] = None
    data_source: Optional[str] = None
