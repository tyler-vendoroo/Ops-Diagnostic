"""Leads API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.lead import LeadCapture
from app.services.lead_service import LeadService


class DoorCountUpdate(BaseModel):
    door_count: int


router = APIRouter()


@router.post("")
async def create_lead(lead: LeadCapture):
    service = LeadService()
    lead_id = await service.create_lead(lead)
    return {"lead_id": lead_id}


@router.patch("/{id}/door-count")
async def update_door_count(id: str, body: DoorCountUpdate):
    service = LeadService()
    await service.update_door_count(id, body.door_count)
    return {"ok": True}


@router.get("/{id}")
async def get_lead(id: str):
    service = LeadService()
    lead = await service.get_lead(id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead
