from fastapi import APIRouter
from data_store import invoices

router = APIRouter()

@router.get("/invoices")
def get_invoices():
    return invoices