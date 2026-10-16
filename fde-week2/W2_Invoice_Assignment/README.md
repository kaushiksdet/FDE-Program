# Invoice Assignment

The FastAPI app reads and writes invoices in `data/invoices.json`. Run it with:

```bash
cd InvoicePayment
uvicorn main:app --reload
```

`GET /invoices/analysis` reports:

* vendor-name variants that are equivalent after removing trailing spaces and
applying case-insensitive comparison;
* credit notes matched to an unused positive invoice from the same vendor and
absolute amount, where the positive invoice date is earlier;
* unmatched negative invoices;
* exact duplicate rows (all fields equal); and
* suspected duplicate row pairs (same normalized vendor, amount, and date, but
different invoice IDs).

Rows in analysis results are numbered starting at 1, matching their position in
`data/invoices.json`. Invalid or missing invoice dates cause the analysis
endpoint to return `422`.

## Processing and payment reconciliation

`POST /invoices/process` normalizes vendor names (strip and title-case) and
statuses (uppercase), reports missing-amount rows by zero-based index, removes
exact duplicate rows while preserving the first, reports suspected duplicate
pairs without removing them, matches earlier positive invoices to negative
credit notes, and marks matched invoices `CANCELLED`. The normalized,
deduplicated, and cancelled invoice data is saved to `data/invoices.json`.
Unmatched credit notes are included in the response and printed to the
application output. Missing-amount and matched/cancelled rows are excluded from
totals; unmatched negative invoice amounts remain in the net totals.

The processing response includes vendor totals and payment reconciliation;
`GET /invoices/reconciliation` returns the current reconciliation without
re-running processing. Payments are summed by `invoice\_id`; unknown payment
invoice IDs are reported during processing.

## Payment endpoints

Payments are stored in `data/payment.json`. The API supports:

|Method|Path|Behavior|
|-|-|-|
|`GET`|`/payments`|List all payments|
|`GET`|`/payments/by-invoice/{invoice\_id}`|List payments for an invoice|
|`GET`|`/payments/{payment\_index}`|Get a payment by its zero-based list index|
|`POST`|`/payments`|Add a payment; its invoice must exist|
|`PUT`|`/payments/{payment\_index}`|Replace a payment by its zero-based list index|
|`DELETE`|`/payments/{payment\_index}`|Delete a payment by its zero-based list index|

Invalid request bodies return `422`; missing invoices or payment indexes return
`404`. Index-based payment paths are used because the existing payment records
do not have payment IDs and can contain multiple entries for one invoice.

Focused rule tests can be run from the repository root:

```bash
python3 -m unittest discover -s InvoicePayment -p 'test\*.py'
```

