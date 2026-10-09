from fastapi import FastAPI
from createInvoice import create_invoice_router
from getInvoices import get_invoice_router
from deleteInvoice import delete_invoice_router
app = FastAPI()

app.include_router(create_invoice_router)
app.include_router(get_invoice_router)
app.include_router(delete_invoice_router)