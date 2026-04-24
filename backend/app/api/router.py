from fastapi import APIRouter
from app.api import diagnostic, internal_auth, leads, reports, webhooks, bookings

router = APIRouter()
router.include_router(diagnostic.router, prefix="/diagnostic", tags=["diagnostic"])
router.include_router(leads.router, prefix="/leads", tags=["leads"])
router.include_router(reports.router, prefix="/reports", tags=["reports"])
router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
router.include_router(internal_auth.router, prefix="/internal", tags=["internal"])
router.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
