"""Diagnostic API endpoints."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select

from app.models.survey import SurveyResponse
from app.models.input_data import ClientInfo
from app.models.lead import LeadCapture
from app.services.diagnostic_service import DiagnosticService
from app.db.database import AsyncSessionLocal
from app.db import models as db_models

router = APIRouter()


class QuickDiagnosticRequest(BaseModel):
    lead: LeadCapture
    survey: SurveyResponse
    client_info: ClientInfo


@router.post("/quick")
async def quick_diagnostic(request: QuickDiagnosticRequest):
    """Run a quick diagnostic from survey answers and return scored results.

    The full pipeline runs synchronously within this request:
    survey → metrics → scores → findings/gaps → tier → PDF (optional) → DB.
    """
    service = DiagnosticService()
    result = await service.run_quick_diagnostic(request.survey, request.client_info)

    return {
        "diagnostic_id": result.diagnostic_id,
        "overall_score": result.overall_score,
        "scores": result.scores,
        "tier": result.tier,
        "key_findings": result.key_findings,
        "gaps": result.gaps,
        "pdf_url": (
            f"/api/v1/diagnostic/{result.diagnostic_id}/pdf"
            if result.pdf_bytes else None
        ),
        "status": result.status,
    }


@router.post("/full")
async def full_diagnostic():
    return {"status": "not_implemented"}


@router.get("/{id}")
async def get_diagnostic(id: str):
    """Fetch a stored diagnostic record by ID."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(db_models.Diagnostic).where(db_models.Diagnostic.id == id)
        )
        record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=404, detail=f"Diagnostic '{id}' not found.")

    scores = record.scores or {}
    overall_score = scores.pop("overall", None)

    return {
        "diagnostic_id": record.id,
        "diagnostic_type": record.diagnostic_type,
        "status": record.status,
        "overall_score": overall_score,
        "scores": scores,
        "tier": record.tier,
        "pdf_url": (
            f"/api/v1/diagnostic/{record.id}/pdf"
            if record.pdf_data else None
        ),
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


@router.get("/{id}/pdf")
async def get_diagnostic_pdf(id: str):
    """Return the stored PDF bytes for a diagnostic."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(db_models.Diagnostic).where(db_models.Diagnostic.id == id)
        )
        record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=404, detail=f"Diagnostic '{id}' not found.")

    if not record.pdf_data:
        raise HTTPException(
            status_code=404,
            detail="PDF not available for this diagnostic. It may have failed to generate.",
        )

    return Response(
        content=record.pdf_data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="diagnostic-{id}.pdf"',
        },
    )
