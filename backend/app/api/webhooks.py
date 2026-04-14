from fastapi import APIRouter
router = APIRouter()

@router.post("/revenue-hero")
async def revenue_hero_webhook():
    return {"status": "not_implemented"}
