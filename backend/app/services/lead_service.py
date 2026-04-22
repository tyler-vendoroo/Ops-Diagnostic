"""LeadService: handles lead persistence in the database."""

import logging
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db import models as db_models
from app.models.lead import LeadCapture

logger = logging.getLogger(__name__)


class LeadService:
    """Manages lead creation and retrieval."""

    async def create_lead(self, lead: LeadCapture) -> str:
        """Create a lead in the DB and return its lead_id.

        If a lead with the same email already exists, return the existing
        lead_id rather than creating a duplicate.
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(db_models.Lead).where(db_models.Lead.email == lead.email)
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                # Update mutable fields that may have changed since first submission
                if lead.phone:
                    existing.phone = lead.phone
                if lead.trial_interest:
                    existing.trial_interest = lead.trial_interest
                await session.commit()
                logger.info(
                    "Lead already exists for email %s — updated and returning id %s",
                    lead.email,
                    existing.id,
                )
                return existing.id

            record = db_models.Lead(
                name=lead.name,
                email=lead.email,
                company=lead.company,
                phone=lead.phone,
                event_source=lead.event_source,
                pms_platform=lead.pms_platform,
                terms_accepted=lead.terms_accepted,
                trial_interest=lead.trial_interest,
                status="new",
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            logger.info("Created new lead %s for email %s", record.id, record.email)
            return record.id

    async def get_lead(self, lead_id: str) -> db_models.Lead | None:
        """Fetch a lead by id. Returns None if not found."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(db_models.Lead).where(db_models.Lead.id == lead_id)
            )
            return result.scalar_one_or_none()

    async def update_door_count(self, lead_id: str, door_count: int) -> None:
        """Set door_count on an existing lead."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(db_models.Lead).where(db_models.Lead.id == lead_id)
            )
            record = result.scalar_one_or_none()
            if record is None:
                logger.warning("update_door_count: lead %s not found", lead_id)
                return
            record.door_count = door_count
            await session.commit()
            logger.info("Updated lead %s door_count to %d", lead_id, door_count)

    async def update_pms_platform(self, lead_id: str, pms_platform: str) -> None:
        """Set pms_platform on an existing lead (overwrites if already set)."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(db_models.Lead).where(db_models.Lead.id == lead_id)
            )
            record = result.scalar_one_or_none()
            if record is None:
                logger.warning("update_pms_platform: lead %s not found", lead_id)
                return
            record.pms_platform = pms_platform
            await session.commit()
            logger.info("Updated lead %s pms_platform to %s", lead_id, pms_platform)

    async def update_status(self, lead_id: str, status: str) -> None:
        """Update the status field of an existing lead."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(db_models.Lead).where(db_models.Lead.id == lead_id)
            )
            record = result.scalar_one_or_none()
            if record is None:
                logger.warning("update_status: lead %s not found", lead_id)
                return
            record.status = status
            await session.commit()
            logger.info("Updated lead %s status to %s", lead_id, status)
