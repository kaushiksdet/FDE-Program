from fastapi import APIRouter
from data_store import invoices
from models import Invoice

router = APIRouter()

@router.post("/invoices")
def create_invoice(invoice: Invoice):
    new_invoice = invoice.model_dump()
    invoice_id = len(invoices) + 1
    new_invoice["id"] = invoice_id
    invoices.append(new_invoice)
    return {"message": "Invoice created successfully", "invoice": new_invoice}
