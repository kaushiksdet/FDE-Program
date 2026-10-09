
import csv
with open('/Users/reach/Documents/fde-week1/src/homeassignments/homework_invoices.csv', 'r') as file:
    reader = csv.DictReader(file)
   
    validInvoice=0
    invalidInvoiceCount=0
    totalInvoices=0
    for row in reader:
        totalInvoices=totalInvoices+1
        try:
            amount = float(row['amount'])
        except (ValueError, TypeError):
            invalidInvoiceCount += 1
            print('invalid amount:', row['amount'])
            continue

        if amount > 10000:
            validInvoice += 1
            print('valid amount:', amount)
        else:
            invalidInvoiceCount += 1
            
            
    print(f"Total Invoices: {totalInvoices}")
    print(f"Valid Invoices: {validInvoice}")
    print(f"Invalid Invoices: {invalidInvoiceCount}")    
