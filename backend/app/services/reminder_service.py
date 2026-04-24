"""Reminder service — sends drip emails to quick-only diagnostic completers."""

import hashlib
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.db.database import AsyncSessionLocal
from app.db import models as db_models
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

# Touch 1 at 48hrs, Touch 2 at 7 days, Touch 3 at 14 days
TOUCH_SCHEDULE = [
    {"touch": 1, "min_age_hours": 48},
    {"touch": 2, "min_age_hours": 168},
    {"touch": 3, "min_age_hours": 336},
]
MAX_REMINDERS = 3
MIN_HOURS_BETWEEN_TOUCHES = 48


async def run_reminder_check() -> int:
    """Check for leads that need a reminder and send the appropriate touch."""
    email_service = EmailService()
    now = datetime.utcnow()
    sent_count = 0

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(db_models.Lead)
            .options(selectinload(db_models.Lead.diagnostics))
            .where(
                and_(
                    db_models.Lead.reminder_count < MAX_REMINDERS,
                    db_models.Lead.email.isnot(None),
                )
            )
            .order_by(db_models.Lead.created_at.asc())
        )
        leads = result.scalars().all()

        for lead in leads:
            diags = lead.diagnostics or []
            quick_diags = [d for d in diags if d.diagnostic_type == "quick" and d.status == "complete"]
            full_diags = [d for d in diags if d.diagnostic_type == "full" and d.status == "complete"]

            if not quick_diags or full_diags:
                continue

            latest_quick = max(quick_diags, key=lambda d: d.created_at or datetime.min)
            diag_age_hours = (now - latest_quick.created_at).total_seconds() / 3600

            next_touch = lead.reminder_count + 1
            if next_touch > MAX_REMINDERS:
                continue

            schedule = TOUCH_SCHEDULE[next_touch - 1]

            if diag_age_hours < schedule["min_age_hours"]:
                continue

            if lead.last_reminder_sent_at:
                hours_since_last = (now - lead.last_reminder_sent_at).total_seconds() / 3600
                if hours_since_last < MIN_HOURS_BETWEEN_TOUCHES:
                    continue

            prefill_token = hashlib.sha256(
                f"{lead.id}:{latest_quick.id}".encode()
            ).hexdigest()[:16]

            overall_score = 0
            if latest_quick.scores and isinstance(latest_quick.scores, dict):
                overall_score = int(latest_quick.scores.get("overall", 0))

            try:
                if next_touch == 1:
                    await email_service.send_reminder_touch_1(
                        lead_email=lead.email,
                        lead_name=lead.name,
                        diagnostic_id=latest_quick.id,
                        overall_score=overall_score,
                        prefill_token=prefill_token,
                    )
                elif next_touch == 2:
                    await email_service.send_reminder_touch_2(
                        lead_email=lead.email,
                        lead_name=lead.name,
                        diagnostic_id=latest_quick.id,
                        overall_score=overall_score,
                        prefill_token=prefill_token,
                    )
                elif next_touch == 3:
                    await email_service.send_reminder_touch_3(
                        lead_email=lead.email,
                        lead_name=lead.name,
                    )

                lead.reminder_count = next_touch
                lead.last_reminder_sent_at = now
                await session.commit()
                sent_count += 1
                logger.info(
                    "Sent reminder touch %d to %s (%s)",
                    next_touch, lead.email, lead.company,
                )

            except Exception as exc:
                logger.error("Reminder failed for lead %s: %s", lead.id, exc)

    logger.info("Reminder check complete. Sent %d reminders.", sent_count)
    return sent_count
