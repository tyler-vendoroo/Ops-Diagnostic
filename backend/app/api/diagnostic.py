from fastapi import APIRouter
router = APIRouter()

@router.post("/quick")
async def quick_diagnostic():
    return {"status": "not_implemented"}

@router.post("/full")
async def full_diagnostic():
    return {"status": "not_implemented"}

@router.get("/{id}")
async def get_diagnostic(id: str):
    return {"status": "not_implemented"}

@router.get("/{id}/pdf")
async def get_diagnostic_pdf(id: str):
    return {"status": "not_implemented"}
