from fastapi import APIRouter
router = APIRouter()

@router.get("/{id}/pdf")
async def get_report_pdf(id: str):
    return {"status": "not_implemented"}

@router.get("/{id}/html")
async def get_report_html(id: str):
    return {"status": "not_implemented"}
