"""Leads API endpoints."""

import hashlib

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.internal_auth import verify_internal_token
from app.db import models as db_models
from app.db.database import AsyncSessionLocal
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


@router.get("")
async def list_leads(
    search: str = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    authed: bool = Depends(verify_internal_token),
):
    """List leads with diagnostics. Searchable by name, email, or company."""
    async with AsyncSessionLocal() as session:
        query = (
            select(db_models.Lead)
            .options(selectinload(db_models.Lead.diagnostics))
            .order_by(db_models.Lead.created_at.desc())
        )

        if search:
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    db_models.Lead.name.ilike(term),
                    db_models.Lead.email.ilike(term),
                    db_models.Lead.company.ilike(term),
                )
            )

        total = (await session.execute(
            select(func.count()).select_from(query.subquery())
        )).scalar() or 0

        leads = (await session.execute(query.offset(offset).limit(limit))).scalars().all()

        return {
            "total": total,
            "leads": [
                {
                    "id": lead.id,
                    "name": lead.name,
                    "email": lead.email,
                    "company": lead.company,
                    "phone": lead.phone,
                    "pms_platform": lead.pms_platform,
                    "trial_interest": lead.trial_interest,
                    "status": lead.status,
                    "created_at": lead.created_at.isoformat() if lead.created_at else None,
                    "referral_code": lead.referral_code,
                    "referred_by": lead.referred_by,
                    "reminder_count": lead.reminder_count or 0,
                    "last_reminder_sent_at": lead.last_reminder_sent_at.isoformat() if lead.last_reminder_sent_at else None,
                    # Enrichment — populated after diagnostic completes
                    "door_count": lead.door_count,
                    "property_count": lead.property_count,
                    "staff_count": lead.staff_count,
                    "operational_model": lead.operational_model,
                    "primary_goal": lead.primary_goal,
                    "overall_score": lead.overall_score,
                    "recommended_tier": lead.recommended_tier,
                    "gap_count": lead.gap_count,
                    "top_gap": lead.top_gap,
                    "pain_points": lead.pain_points,
                    "after_hours_method": lead.after_hours_method,
                    "avg_response_time": lead.avg_response_time,
                    "projected_score": lead.projected_score,
                    "diagnostics": [
                        {
                            "id": d.id,
                            "type": d.diagnostic_type,
                            "status": d.status,
                            "overall_score": d.scores.get("overall") if d.scores else None,
                            "tier": d.tier,
                            "created_at": d.created_at.isoformat() if d.created_at else None,
                        }
                        for d in (lead.diagnostics or [])
                    ],
                }
                for lead in leads
            ],
        }


@router.patch("/{id}/door-count")
async def update_door_count(id: str, body: DoorCountUpdate):
    service = LeadService()
    await service.update_door_count(id, body.door_count)
    return {"ok": True}


@router.get("/prefill/{token}")
async def get_prefill_data(token: str):
    """Retrieve client info for pre-filling the full diagnostic form from an email link."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(db_models.Lead)
            .options(selectinload(db_models.Lead.diagnostics))
            .order_by(db_models.Lead.created_at.desc())
            .limit(200)
        )
        leads = result.scalars().all()

        for lead in leads:
            for diag in (lead.diagnostics or []):
                check = hashlib.sha256(
                    f"{lead.id}:{diag.id}".encode()
                ).hexdigest()[:16]
                if check == token:
                    summary = diag.summary or {}
                    return {
                        "company_name": summary.get("company_name") or lead.company,
                        "door_count": summary.get("door_count"),
                        "property_count": summary.get("property_count"),
                        "pms_platform": lead.pms_platform,
                        "operational_model": summary.get("operational_model"),
                        "staff_count": summary.get("staff_count"),
                        "primary_goal": summary.get("primary_goal"),
                    }

        raise HTTPException(status_code=404, detail="Prefill token not found")



@router.get("/{id}")
async def get_lead(id: str):
    service = LeadService()
    lead = await service.get_lead(id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead
