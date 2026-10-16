import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_FILE = DATA_DIR / "invoices.json"
PAYMENT_FILE = DATA_DIR / "payment.json"

def load_invoices():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_invoices(invoices):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(invoices, f, indent=4)


def load_payments():
    with open(PAYMENT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_payments(payments):
    with open(PAYMENT_FILE, "w", encoding="utf-8") as f:
        json.dump(payments, f, indent=4)


def find_invoice_by_id(invoice_id):
    invoices = load_invoices()
    for invoice in invoices:
        if invoice["invoice_id"] == invoice_id:
            return invoice
    return None 


def add_invoice(invoice):
    invoices = load_invoices()
    invoices.append(invoice)
    save_invoices(invoices)


def update_invoice(invoice_id, updated_invoice):    
    invoices = load_invoices()
    for index, invoice in enumerate(invoices):
        if invoice["invoice_id"] == invoice_id:
            invoices[index] = updated_invoice
            save_invoices(invoices)
            return True
    return False  


def delete_invoice(invoice_id):
    invoices = load_invoices()
    for index, invoice in enumerate(invoices):
        if invoice["invoice_id"] == invoice_id:
            del invoices[index]
            save_invoices(invoices)
            return True
    return False


def find_payment_by_index(payment_index):
    payments = load_payments()
    if payment_index < 0 or payment_index >= len(payments):
        return None
    return payments[payment_index]


def add_payment(payment):
    payments = load_payments()
    payments.append(payment)
    save_payments(payments)
    return len(payments) - 1


def update_payment(payment_index, updated_payment):
    payments = load_payments()
    if payment_index < 0 or payment_index >= len(payments):
        return False
    payments[payment_index] = updated_payment
    save_payments(payments)
    return True


def delete_payment(payment_index):
    payments = load_payments()
    if payment_index < 0 or payment_index >= len(payments):
        return False
    del payments[payment_index]
    save_payments(payments)
    return True

    