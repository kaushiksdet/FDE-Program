from pydantic import BaseModel

class Invoice(BaseModel):
    invoice_id: str
    vendor: str
    amount: float
    status: str