from pydantic import BaseModel

class Invoice(BaseModel):
    id: int
    amount: float
    status: str

class Employee(BaseModel):
    name: str
    department: str
