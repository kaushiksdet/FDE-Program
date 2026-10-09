
from fastapi import APIRouter

get_invoice_router = APIRouter()

@get_invoice_router.get("/invoices")
def get_invoices():
    import json
    with open('/Users/reach/Documents/fde-week1/src/homeassignments/invoices.json', 'r') as file:
        invoices = json.load(file)
        totalInvoices = len(invoices)
    return {
            "Total Invoices": totalInvoices,
            "all Invoices": invoices
}


@get_invoice_router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: str):
    import json

    with open('/Users/reach/Documents/fde-week1/src/homeassignments/invoices.json', 'r') as file:
        invoices = json.load(file)

        for invoice in invoices:
            if invoice["invoice_id"] == invoice_id:
                return invoice

        return {"error": "Invoice not found"}

