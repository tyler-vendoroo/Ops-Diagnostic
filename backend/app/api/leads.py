from fastapi import APIRouter
router = APIRouter()

@router.post("")
async def create_lead():
    return {"status": "not_implemented"}

@router.get("/{id}")
async def get_lead(id: str):
    return {"status": "not_implemented"}
