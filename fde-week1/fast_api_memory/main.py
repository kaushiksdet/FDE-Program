import importlib
from fastapi import FastAPI

create_invoice = importlib.import_module("03_create_invoice").router
get_invoices = importlib.import_module("01_get_invoices").router

app = FastAPI()
app.include_router(create_invoice)
app.include_router(get_invoices)

create_employee = importlib.import_module("04_create_employee").router
get_employees = importlib.import_module("02_get_employees").router

app.include_router(create_employee)
app.include_router(get_employees)
