from fastapi import FastAPI, HTTPException
from models import Invoice, Payment
from services import (
    analyze_invoices,
    create_invoice,
    create_payment,
    delete_invoice,
    delete_payment,
    get_invoice,
    get_payment,
    list_payments,
    process_invoices,
    reconcile_payments,
    update_invoice,
    update_payment,
)

app = FastAPI()


@app.get("/invoices/analysis")
def read_invoice_analysis():
    try:
        return analyze_invoices()
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/invoices/process")
def process_invoice_data():
    try:
        return process_invoices()
    except (ValueError, OSError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/invoices/reconciliation")
def read_payment_reconciliation():
    try:
        return reconcile_payments()
    except (ValueError, OSError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/invoices/{invoice_id}", response_model=Invoice)
def read_invoice(invoice_id: str):
    try:
        return get_invoice(invoice_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/invoices", response_model=Invoice)
def create_new_invoice(invoice: Invoice):
    return create_invoice(invoice.model_dump())

@app.put("/invoices/{invoice_id}", response_model=Invoice)
def update_existing_invoice(invoice_id: str, updated_invoice: Invoice):
    try:
        return update_invoice(invoice_id, updated_invoice.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.delete("/invoices/{invoice_id}")
def delete_existing_invoice(invoice_id: str):
    try:
        delete_invoice(invoice_id)
        return {"detail": "Invoice deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/payments", response_model=list[Payment])
def read_payments():
    try:
        return list_payments()
    except (ValueError, OSError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/payments/by-invoice/{invoice_id}", response_model=list[Payment])
def read_payments_for_invoice(invoice_id: str):
    try:
        return list_payments(invoice_id)
    except (ValueError, OSError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/payments/{payment_index}", response_model=Payment)
def read_payment(payment_index: int):
    try:
        return get_payment(payment_index)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/payments", response_model=Payment, status_code=201)
def create_new_payment(payment: Payment):
    try:
        return create_payment(payment.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.put("/payments/{payment_index}", response_model=Payment)
def update_existing_payment(payment_index: int, payment: Payment):
    try:
        return update_payment(payment_index, payment.model_dump())
    except ValueError as error:
        status_code = 404 if "not found" in str(error).lower() else 422
        raise HTTPException(status_code=status_code, detail=str(error)) from error


@app.delete("/payments/{payment_index}")
def delete_existing_payment(payment_index: int):
    try:
        delete_payment(payment_index)
        return {"detail": "Payment deleted successfully"}
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error