"""Diagnostic API endpoints."""

import json
import uuid
import asyncio
import logging

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from typing import Optional

from app.models.survey import SurveyResponse
from app.models.input_data import ClientInfo
from app.models.lead import LeadCapture
from app.services.diagnostic_service import DiagnosticService
from app.services.lead_service import LeadService
from app.db.database import AsyncSessionLocal
from app.db import models as db_models

logger = logging.getLogger(__name__)

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
    result = await service.run_quick_diagnostic(request.survey, request.client_info, request.lead)

    # Persist PMS platform selection on the lead record
    pms = request.survey.pms_platform
    if pms:
        lead_service = LeadService()
        lead_id = await lead_service.create_lead(request.lead)
        await lead_service.update_pms_platform(lead_id, pms)

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
        "summary": result.summary,
    }


async def _run_full_diagnostic_background(
    diagnostic_id: str,
    work_order_bytes: bytes,
    work_order_filename: str,
    client_info_dict: dict,
    lease_bytes: bytes | None,
    pma_bytes: bytes | None,
    vendor_directory_bytes: bytes | None,
    lead_id: str | None,
) -> None:
    """Background task: delegate to DiagnosticService; mark failed if not yet implemented."""
    service = DiagnosticService()
    try:
        await service.run_full_diagnostic(
            diagnostic_id=diagnostic_id,
            work_order_bytes=work_order_bytes,
            work_order_filename=work_order_filename,
            client_info=client_info_dict,
            lease_bytes=lease_bytes,
            pma_bytes=pma_bytes,
            vendor_directory_bytes=vendor_directory_bytes,
            lead_id=lead_id,
        )
    except NotImplementedError as exc:
        logger.info("Full diagnostic not yet implemented — marking %s as failed.", diagnostic_id)
        await asyncio.sleep(2)
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(db_models.Diagnostic).where(db_models.Diagnostic.id == diagnostic_id)
            )
            record = result.scalar_one_or_none()
            if record is not None:
                record.status = "failed"
                record.error = str(exc)
                await session.commit()
    except Exception as exc:
        logger.error("Full diagnostic background task failed for %s: %s", diagnostic_id, exc)
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(db_models.Diagnostic).where(db_models.Diagnostic.id == diagnostic_id)
            )
            record = result.scalar_one_or_none()
            if record is not None:
                record.status = "failed"
                record.error = str(exc)
                await session.commit()


@router.post("/full")
async def full_diagnostic(
    background_tasks: BackgroundTasks,
    work_order_file: UploadFile = File(...),
    lease_file: Optional[UploadFile] = File(None),
    pma_file: Optional[UploadFile] = File(None),
    vendor_directory_file: Optional[UploadFile] = File(None),
    client_info: str = Form(...),
    lead_id: Optional[str] = Form(None),
):
    """Accept uploaded diagnostic files, create a DB record, and process in the background."""
    # Parse client info
    try:
        client_info_dict = json.loads(client_info)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid client_info JSON: {exc}") from exc

    # Read file bytes into memory
    work_order_bytes = await work_order_file.read()
    lease_bytes = await lease_file.read() if lease_file else None
    pma_bytes = await pma_file.read() if pma_file else None
    vendor_directory_bytes = await vendor_directory_file.read() if vendor_directory_file else None

    # Create diagnostic record immediately so the frontend can poll it
    diagnostic_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        record = db_models.Diagnostic(
            id=diagnostic_id,
            lead_id=lead_id or None,
            diagnostic_type="full",
            status="processing",
            scores=None,
            tier=None,
            pdf_data=None,
            pdf_path=None,
            error=None,
        )
        session.add(record)
        await session.commit()

    # Persist PMS platform selection on the lead record
    pms = client_info_dict.get("pms_platform")
    if lead_id and pms:
        lead_service = LeadService()
        await lead_service.update_pms_platform(lead_id, pms)

    # Queue background processing
    background_tasks.add_task(
        _run_full_diagnostic_background,
        diagnostic_id=diagnostic_id,
        work_order_bytes=work_order_bytes,
        work_order_filename=work_order_file.filename or "work_orders",
        client_info_dict=client_info_dict,
        lease_bytes=lease_bytes,
        pma_bytes=pma_bytes,
        vendor_directory_bytes=vendor_directory_bytes,
        lead_id=lead_id,
    )

    return {"diagnostic_id": diagnostic_id, "status": "processing"}


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
        "error": record.error,
        "overall_score": overall_score,
        "scores": scores,
        "tier": record.tier,
        "key_findings": record.key_findings or [],
        "gaps": record.gaps or [],
        "pdf_url": (
            f"/api/v1/diagnostic/{record.id}/pdf"
            if record.pdf_data else None
        ),
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "summary": record.summary,
    }


@router.get("/{id}/report")
async def get_diagnostic_report(id: str):
    """Return the full HTML report for inline browser viewing."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(db_models.Diagnostic).where(db_models.Diagnostic.id == id)
        )
        record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=404, detail=f"Diagnostic '{id}' not found.")

    if not record.html_report:
        raise HTTPException(
            status_code=404,
            detail="HTML report not available for this diagnostic.",
        )

    return HTMLResponse(content=record.html_report)


@router.get("/{id}/pdf")
async def get_diagnostic_pdf(id: str):
    """Return PDF bytes for a diagnostic, regenerating from stored HTML if needed."""
    from app.report.generator import generate_pdf_async

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(db_models.Diagnostic).where(db_models.Diagnostic.id == id)
        )
        record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=404, detail=f"Diagnostic '{id}' not found.")

    pdf_bytes = record.pdf_data

    if not pdf_bytes:
        if not record.html_report:
            raise HTTPException(
                status_code=404,
                detail="PDF not available — no stored HTML to regenerate from.",
            )
        # Regenerate from stored HTML and cache it for future requests
        try:
            pdf_bytes = await generate_pdf_async(record.html_report)
            async with AsyncSessionLocal() as session:
                rec = await session.get(db_models.Diagnostic, id)
                if rec:
                    rec.pdf_data = pdf_bytes
                    await session.commit()
        except Exception as exc:
            logger.error("PDF regeneration failed for %s: %s", id, exc)
            raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="diagnostic-{id}.pdf"',
        },
    )


@router.post("/{id}/send-results")
async def send_diagnostic_results_email(id: str):
    """Send the diagnostic results link to the associated lead's email."""
    from app.config import settings

    async with AsyncSessionLocal() as session:
        diag = (await session.execute(
            select(db_models.Diagnostic).where(db_models.Diagnostic.id == id)
        )).scalar_one_or_none()

        if diag is None:
            raise HTTPException(status_code=404, detail="Diagnostic not found.")
        if not diag.lead_id:
            raise HTTPException(status_code=400, detail="No lead associated with this diagnostic.")

        lead = await session.get(db_models.Lead, diag.lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found.")

    first_name = lead.name.split()[0] if lead.name else lead.name
    # Full diagnostics link to the full branded HTML report; quick to the summary page
    if diag.diagnostic_type == "full" and diag.html_report:
        results_url = f"{settings.api_url}/api/v1/diagnostic/{id}/report"
    else:
        results_url = f"{settings.frontend_url}/diagnostic/results/{id}"
    schedule_url = f"{settings.frontend_url}/schedule"

    try:
        import asyncio
        import resend

        resend.api_key = settings.resend_api_key
        html = f"""
<div style="font-family:-apple-system,sans-serif;max-width:520px;margin:0 auto;padding:32px;">
  <div style="background:#1a1a2e;padding:24px 32px;border-radius:12px 12px 0 0;">
    <p style="margin:0;color:#039cac;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;">Vendoroo Operations Diagnostic</p>
    <h1 style="margin:8px 0 0;color:white;font-size:20px;">Your diagnostic results</h1>
  </div>
  <div style="background:white;padding:24px 32px;border:1px solid #f1f5f9;border-top:none;border-radius:0 0 12px 12px;">
    <p style="margin:0 0 16px;color:#334155;font-size:15px;">Hi {first_name},</p>
    <p style="margin:0 0 20px;color:#64748b;font-size:14px;line-height:1.6;">
      Here&apos;s a link to your Vendoroo operations diagnostic — it shows how your portfolio
      benchmarks against AI-managed operations and where the biggest opportunities are.
    </p>
    <div style="text-align:center;margin:24px 0;">
      <a href="{results_url}" style="display:inline-block;background:#039cac;color:#ffffff;font-size:14px;font-weight:600;padding:14px 32px;border-radius:50px;text-decoration:none;">
        View My Diagnostic Results
      </a>
    </div>
    <p style="margin:20px 0 0;color:#64748b;font-size:13px;line-height:1.6;">
      Want to walk through the findings together?
      <a href="{schedule_url}" style="color:#039cac;text-decoration:none;font-weight:600;">Book a meeting with us</a>
      and we&apos;ll go through every data point and answer your questions.
    </p>
    <hr style="margin:24px 0;border:none;border-top:1px solid #f1f5f9;">
    <p style="margin:0;color:#94a3b8;font-size:12px;">Questions? Reply to this email — we&apos;re happy to help.</p>
  </div>
</div>"""

        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: resend.Emails.send({
                "from": settings.diagnostic_from_email,
                "to": [lead.email],
                "subject": f"Your Vendoroo diagnostic results, {first_name}",
                "html": html,
            }),
        )
        logger.info("Sent diagnostic results email to %s for diagnostic %s", lead.email, id)
    except Exception as exc:
        logger.error("Failed to send results email for diagnostic %s: %s", id, exc)
        raise HTTPException(status_code=500, detail=f"Email send failed: {exc}")

    return {"ok": True, "email": lead.email}
