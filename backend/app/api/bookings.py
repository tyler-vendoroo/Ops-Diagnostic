"""Booth booking API for NARPM conference meetings."""

import logging
from datetime import date, time, datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func

from app.db.database import AsyncSessionLocal
from app.db import models as db_models
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

CONFERENCE_DAYS = [
    date(2026, 4, 28),
    date(2026, 4, 29),
    date(2026, 4, 30),
]
START_HOUR = 9
END_HOUR = 16
SLOT_MINUTES = 15
MAX_PER_SLOT = 4


class BookingRequest(BaseModel):
    name: str
    email: str
    company: str | None = None
    booking_date: str
    booking_time: str
    notes: str | None = None
    lead_id: str | None = None


@router.get("/slots")
async def get_available_slots():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(db_models.BoothBooking).where(
                db_models.BoothBooking.status == "confirmed"
            )
        )
        bookings = result.scalars().all()

        booked: dict[str, int] = {}
        for b in bookings:
            key = f"{b.booking_date}|{b.booking_time}"
            booked[key] = booked.get(key, 0) + 1

        now_ct = datetime.utcnow() - timedelta(hours=5)

        days = []
        for conf_date in CONFERENCE_DAYS:
            slots = []
            current = datetime.combine(conf_date, time(START_HOUR, 0))
            end = datetime.combine(conf_date, time(END_HOUR, 0))

            while current < end:
                slot_time = current.time()
                key = f"{conf_date}|{slot_time}"
                taken = booked.get(key, 0)

                if datetime.combine(conf_date, slot_time) > now_ct:
                    slots.append({
                        "time": slot_time.strftime("%H:%M"),
                        "display": current.strftime("%-I:%M %p"),
                        "available": taken < MAX_PER_SLOT,
                    })

                current += timedelta(minutes=SLOT_MINUTES)

            days.append({
                "date": conf_date.isoformat(),
                "display": conf_date.strftime("%A, %B %d"),
                "slots": slots,
            })

        return {"days": days}


@router.post("/book")
async def create_booking(req: BookingRequest):
    try:
        booking_date = date.fromisoformat(req.booking_date)
        hour, minute = req.booking_time.split(":")
        booking_time = time(int(hour), int(minute))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid date or time format")

    if booking_date not in CONFERENCE_DAYS:
        raise HTTPException(status_code=400, detail="Not a conference day")

    async with AsyncSessionLocal() as session:
        count_result = await session.execute(
            select(func.count()).select_from(db_models.BoothBooking).where(
                db_models.BoothBooking.booking_date == booking_date,
                db_models.BoothBooking.booking_time == booking_time,
                db_models.BoothBooking.status == "confirmed",
            )
        )
        count = count_result.scalar() or 0

        if count >= MAX_PER_SLOT:
            raise HTTPException(status_code=409, detail="This time slot is no longer available")

        booking = db_models.BoothBooking(
            name=req.name,
            email=req.email,
            company=req.company,
            booking_date=booking_date,
            booking_time=booking_time,
            notes=req.notes,
            lead_id=req.lead_id,
            status="confirmed",
        )
        session.add(booking)
        await session.commit()
        await session.refresh(booking)

    display_time = datetime.combine(booking_date, booking_time).strftime("%-I:%M %p")
    display_date = booking_date.strftime("%A, %B %d")

    try:
        import asyncio
        import resend

        resend.api_key = settings.resend_api_key
        html = f"""
<div style="font-family:-apple-system,sans-serif;max-width:500px;margin:0 auto;padding:32px;">
  <div style="background:#1a1a2e;padding:24px 32px;border-radius:12px 12px 0 0;">
    <p style="margin:0;color:#039cac;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;">NARPM Broker/Owner 2026</p>
    <h1 style="margin:8px 0 0;color:white;font-size:20px;">You're booked!</h1>
  </div>
  <div style="background:white;padding:24px 32px;border:1px solid #f1f5f9;border-top:none;border-radius:0 0 12px 12px;">
    <p style="margin:0 0 16px;color:#334155;font-size:15px;">Hi {req.name},</p>
    <p style="margin:0 0 24px;color:#64748b;font-size:14px;line-height:1.6;">We'll see you at the Vendoroo booth!</p>
    <div style="background:#f8fafc;border-radius:8px;padding:16px;margin-bottom:24px;">
      <p style="margin:0 0 4px;font-size:13px;color:#94a3b8;">When</p>
      <p style="margin:0 0 12px;font-size:16px;font-weight:600;color:#0F172A;">{display_date} at {display_time} CT</p>
      <p style="margin:0 0 4px;font-size:13px;color:#94a3b8;">Where</p>
      <p style="margin:0;font-size:16px;font-weight:600;color:#0F172A;">Vendoroo &middot; Imperial Room 5A (4th Floor) &middot; Hyatt Regency New Orleans</p>
    </div>
    <p style="margin:0;color:#94a3b8;font-size:12px;">Can&apos;t make your slot? No worries — come find us in Imperial Room 5A anytime during the conference.</p>
  </div>
</div>"""
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: resend.Emails.send({
                "from": settings.diagnostic_from_email,
                "to": [req.email],
                "subject": f"Confirmed: Meet Vendoroo at NARPM — {display_date} at {display_time}",
                "html": html,
            }),
        )
    except Exception as exc:
        logger.warning("Booking confirmation email failed: %s", exc)

    # Include most recent completed diagnostic so the confirmation page can link to it
    diagnostic_id: str | None = None
    if req.lead_id:
        try:
            async with AsyncSessionLocal() as session:
                diag_result = await session.execute(
                    select(db_models.Diagnostic)
                    .where(
                        db_models.Diagnostic.lead_id == req.lead_id,
                        db_models.Diagnostic.status == "complete",
                    )
                    .order_by(db_models.Diagnostic.created_at.desc())
                    .limit(1)
                )
                diag = diag_result.scalar_one_or_none()
                if diag:
                    diagnostic_id = diag.id
        except Exception as exc:
            logger.warning("Could not look up diagnostic for lead %s: %s", req.lead_id, exc)

    return {
        "id": booking.id,
        "date": display_date,
        "time": display_time,
        "status": "confirmed",
        "diagnostic_id": diagnostic_id,
    }


@router.get("/admin")
async def list_bookings():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(db_models.BoothBooking)
            .order_by(db_models.BoothBooking.booking_date, db_models.BoothBooking.booking_time)
        )
        bookings = result.scalars().all()

        output = []
        for b in bookings:
            diagnostic_id = None
            diagnostic_score = None

            lead_id = b.lead_id
            if not lead_id:
                lead_result = await session.execute(
                    select(db_models.Lead).where(db_models.Lead.email == b.email)
                )
                lead = lead_result.scalar_one_or_none()
                if lead:
                    lead_id = lead.id

            if lead_id:
                diag_result = await session.execute(
                    select(db_models.Diagnostic)
                    .where(
                        db_models.Diagnostic.lead_id == lead_id,
                        db_models.Diagnostic.status == "complete",
                    )
                    .order_by(db_models.Diagnostic.created_at.desc())
                    .limit(1)
                )
                diag = diag_result.scalar_one_or_none()
                if diag:
                    diagnostic_id = diag.id
                    if diag.scores and isinstance(diag.scores, dict):
                        diagnostic_score = diag.scores.get("overall")

            output.append({
                "id": b.id,
                "name": b.name,
                "email": b.email,
                "company": b.company,
                "date": b.booking_date.isoformat(),
                "date_display": b.booking_date.strftime("%A, %B %d"),
                "time": b.booking_time.strftime("%H:%M"),
                "time_display": datetime.combine(b.booking_date, b.booking_time).strftime("%-I:%M %p"),
                "notes": b.notes,
                "status": b.status,
                "lead_id": lead_id,
                "diagnostic_id": diagnostic_id,
                "diagnostic_score": int(diagnostic_score) if diagnostic_score is not None else None,
            })

        return {"bookings": output}


@router.post("/{id}/send-results")
async def send_results_email(id: str):
    """Send an email to the booked person with a link to their diagnostic results."""
    async with AsyncSessionLocal() as session:
        booking = (await session.execute(
            select(db_models.BoothBooking).where(db_models.BoothBooking.id == id)
        )).scalar_one_or_none()

        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")

        # Find diagnostic — via booking's lead_id or by email match
        lead_id = booking.lead_id
        if not lead_id:
            lead = (await session.execute(
                select(db_models.Lead).where(db_models.Lead.email == booking.email)
            )).scalar_one_or_none()
            if lead:
                lead_id = lead.id

        diagnostic_id: str | None = None
        diagnostic_type: str = "quick"
        if lead_id:
            diag = (await session.execute(
                select(db_models.Diagnostic)
                .where(
                    db_models.Diagnostic.lead_id == lead_id,
                    db_models.Diagnostic.status == "complete",
                )
                .order_by(db_models.Diagnostic.created_at.desc())
                .limit(1)
            )).scalar_one_or_none()
            if diag:
                diagnostic_id = diag.id
                diagnostic_type = diag.diagnostic_type

    if not diagnostic_id:
        raise HTTPException(status_code=404, detail="No completed diagnostic found for this contact")

    results_url = f"{settings.frontend_url}/diagnostic/results/{diagnostic_id}"
    schedule_url = f"{settings.frontend_url}/schedule"
    first_name = booking.name.split()[0] if booking.name else booking.name

    try:
        import asyncio
        import resend

        resend.api_key = settings.resend_api_key
        html = f"""
<div style="font-family:-apple-system,sans-serif;max-width:520px;margin:0 auto;padding:32px;">
  <div style="background:#1a1a2e;padding:24px 32px;border-radius:12px 12px 0 0;">
    <p style="margin:0;color:#039cac;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;">Vendoroo &middot; NARPM Broker/Owner 2026</p>
    <h1 style="margin:8px 0 0;color:white;font-size:20px;">Your diagnostic results</h1>
  </div>
  <div style="background:white;padding:24px 32px;border:1px solid #f1f5f9;border-top:none;border-radius:0 0 12px 12px;">
    <p style="margin:0 0 16px;color:#334155;font-size:15px;">Hi {first_name},</p>
    <p style="margin:0 0 20px;color:#64748b;font-size:14px;line-height:1.6;">
      Great meeting you at the conference. Here&apos;s a link to your Vendoroo operations diagnostic — it shows
      how your portfolio benchmarks against AI-managed operations and where the biggest opportunities are.
    </p>
    <div style="text-align:center;margin:24px 0;">
      <a href="{results_url}" style="display:inline-block;background:#039cac;color:#ffffff;font-size:14px;font-weight:600;padding:14px 32px;border-radius:50px;text-decoration:none;">
        View My Diagnostic Results
      </a>
    </div>
    <p style="margin:20px 0 0;color:#64748b;font-size:13px;line-height:1.6;">
      Want to walk through the results together? <a href="{schedule_url}" style="color:#039cac;text-decoration:none;font-weight:600;">Book a follow-up call</a> and we&apos;ll go through every finding and answer your questions.
    </p>
    <hr style="margin:24px 0;border:none;border-top:1px solid #f1f5f9;">
    <p style="margin:0;color:#94a3b8;font-size:12px;">
      Attending NARPM? Come find us in Imperial Room 5A (4th Floor) at the Hyatt Regency New Orleans.
    </p>
  </div>
</div>"""

        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: resend.Emails.send({
                "from": settings.diagnostic_from_email,
                "to": [booking.email],
                "subject": f"Your Vendoroo diagnostic results, {first_name}",
                "html": html,
            }),
        )
        logger.info("Sent results email to %s for booking %s", booking.email, id)
    except Exception as exc:
        logger.error("Failed to send results email for booking %s: %s", id, exc)
        raise HTTPException(status_code=500, detail=f"Email send failed: {exc}")

    return {"ok": True, "email": booking.email}
