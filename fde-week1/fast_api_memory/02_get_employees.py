from fastapi import APIRouter
from data_store import employees

router = APIRouter()

@router.get("/employees")
def get_employees():
    return employees

@router.get("/employees/{employee_id}")
def get_employee(employee_id: int):
    for employee in employees:
        if employee["id"] == employee_id:
            return employee
    else:
        return {"message": "Employee not found"}