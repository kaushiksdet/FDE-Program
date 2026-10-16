from pydantic import BaseModel, Field


class Invoice(BaseModel):
    invoice_id: str
    amount: float | None
    status: str
    vendor: str = "UNKNOWN"
    date: str


class Payment(BaseModel):
    invoice_id: str = Field(min_length=1)
    paid: float