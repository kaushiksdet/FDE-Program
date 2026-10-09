from fastapi import APIRouter

delete_invoice_router = APIRouter() 
@delete_invoice_router.delete("/invoices/{invoice_id}")
def delete_invoice(invoice_id: str):    
    import json
    import os

    file_path = '/Users/reach/Documents/fde-week1/src/homeassignments/data/invoices.json'
    temp_file_path = '/Users/reach/Documents/fde-week1/src/homeassignments/invoices.json'

    with open(file_path, 'r') as file:
        invoices = json.load(file)

    invoice_found = False
    updated_invoices = []
    for invoice in invoices:
        if invoice["invoice_id"] != invoice_id:
            updated_invoices.append(invoice)
        else:
            invoice_found = True

    if invoice_found:
        with open(temp_file_path, 'w') as temp_file:
            json.dump(updated_invoices, temp_file, indent=4)

    if invoice_found:
        os.replace(temp_file_path, file_path)
        return {"message": f"Invoice with ID {invoice_id} has been deleted."}
    else:
        os.remove(temp_file_path)  # Clean up the temporary file if no invoice was found
        return {"error": "Invoice not found"}   
    
