import json
from datetime import date as Date

import repository
from models import Invoice, Payment


def _vendor_key(vendor: str) -> str:
    return vendor.strip().casefold()


def _numeric_amount(invoice: dict) -> int | float | None:
    amount = invoice.get("amount")
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        return None
    return amount


def _exact_key(invoice: dict) -> str:
    return json.dumps(
        invoice, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def _print_report(report: dict) -> None:
    for row in report["missing_amount_rows"]:
        print(f"Invoice index {row} has amount None; excluded from totals.")
    print(f"Exact duplicates: {report['exact_dupes']}")
    for pair in report["suspected_duplicates"]:
        print(f"{pair['invoice_ids'][0]} ~ {pair['invoice_ids'][1]}")
    for pair in report["credit_note_pairs"]:
        print(f"{pair[0]} <-> {pair[1]}")
    for row in report["unmatched_credit_note_rows"]:
        print(f"Credit note at index {row} has no partner.")
    print(f"Vendor totals: {report['vendor_totals']}")
    print(f"Payment reconciliation: {report['payment_reconciliation']}")


def analyze_invoice_rows(invoices: list[dict]) -> dict:
    vendor_variants = {}
    parsed_dates = []
    for row_number, invoice in enumerate(invoices, start=1):
        vendor = invoice.get("vendor") or "UNKNOWN"
        if not isinstance(vendor, str):
            raise ValueError(f"Invoice on row {row_number} has an invalid vendor.")
        vendor_variants.setdefault(_vendor_key(vendor), set()).add(vendor)

        raw_date = invoice.get("date")
        try:
            parsed_dates.append(Date.fromisoformat(raw_date))
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"Invoice on row {row_number} has an invalid or missing ISO date."
            ) from error

    vendor_groups = [
        {"vendor_names": sorted(names, key=str.casefold)}
        for names in vendor_variants.values()
        if len(names) > 1
    ]

    exact_groups = []
    for index, invoice in enumerate(invoices):
        for group in exact_groups:
            if invoices[group[0]] == invoice:
                group.append(index)
                break
        else:
            exact_groups.append([index])
    exact_duplicates = [
        {"rows": [index + 1 for index in indexes]}
        for indexes in exact_groups
        if len(indexes) > 1
    ]

    suspected_duplicates = []
    for first_index, first in enumerate(invoices):
        first_amount = first.get("amount")
        if not isinstance(first_amount, (int, float)) or isinstance(first_amount, bool):
            continue
        for second_index in range(first_index + 1, len(invoices)):
            second = invoices[second_index]
            second_amount = second.get("amount")
            if (
                first.get("invoice_id") != second.get("invoice_id")
                and _vendor_key(first.get("vendor") or "UNKNOWN")
                == _vendor_key(second.get("vendor") or "UNKNOWN")
                and first_amount == second_amount
                and first.get("date") == second.get("date")
            ):
                suspected_duplicates.append(
                    {"rows": [first_index + 1, second_index + 1]}
                )

    positive_candidates = {}
    for index, invoice in enumerate(invoices):
        amount = invoice.get("amount")
        if isinstance(amount, (int, float)) and not isinstance(amount, bool) and amount > 0:
            key = (_vendor_key(invoice.get("vendor") or "UNKNOWN"), amount)
            positive_candidates.setdefault(key, []).append(index)

    matched_positives = set()
    credit_notes = []
    unmatched_credit_notes = []
    for credit_index, credit in enumerate(invoices):
        amount = credit.get("amount")
        if not isinstance(amount, (int, float)) or isinstance(amount, bool) or amount >= 0:
            continue

        key = (_vendor_key(credit.get("vendor") or "UNKNOWN"), abs(amount))
        earlier = [
            index
            for index in positive_candidates.get(key, [])
            if index not in matched_positives and parsed_dates[index] < parsed_dates[credit_index]
        ]
        if not earlier:
            unmatched_credit_notes.append({"row": credit_index + 1})
            continue

        positive_index = max(earlier, key=lambda index: parsed_dates[index])
        matched_positives.add(positive_index)
        credit_notes.append(
            {"credit_note_row": credit_index + 1, "canceled_invoice_row": positive_index + 1}
        )

    return {
        "vendor_groups": vendor_groups,
        "credit_notes": credit_notes,
        "unmatched_credit_notes": unmatched_credit_notes,
        "exact_duplicates": exact_duplicates,
        "suspected_duplicates": suspected_duplicates,
    }


def analyze_invoices() -> dict:
    return analyze_invoice_rows(repository.load_invoices())


def process_invoice_rows(invoices: list[dict], payments: list[dict]) -> dict:
    normalized = []
    missing_amount_rows = []
    for index in range(len(invoices)):
        invoice = invoices[index]
        vendor = invoice.get("vendor")
        if vendor is not None and not isinstance(vendor, str):
            raise ValueError(f"Invoice at index {index} has an invalid vendor.")
        invoice["vendor"] = (vendor or "UNKNOWN").strip().title()
        status = invoice.get("status")
        if status is not None and not isinstance(status, str):
            raise ValueError(f"Invoice at index {index} has an invalid status.")
        invoice["status"] = (status or "").upper()
        if invoice.get("amount") is None:
            missing_amount_rows.append(index)
        elif _numeric_amount(invoice) is None:
            raise ValueError(f"Invoice at index {index} has an invalid amount.")
        normalized.append(invoice)

    exact_dupes = {}
    for index in range(len(normalized)):
        key = _exact_key(normalized[index])
        exact_dupes.setdefault(key, []).append(index)
    exact_dupes = {
        key: indexes for key, indexes in exact_dupes.items() if len(indexes) > 1
    }

    duplicate_indexes = {
        index
        for indexes in exact_dupes.values()
        for index in indexes[1:]
    }
    invoices[:] = [
        invoice for index, invoice in enumerate(normalized) if index not in duplicate_indexes
    ]

    suspected_duplicates = []
    for first_index, first in enumerate(invoices):
        first_amount = _numeric_amount(first)
        if first_amount is None:
            continue
        for second_index in range(first_index + 1, len(invoices)):
            second = invoices[second_index]
            second_amount = _numeric_amount(second)
            if (
                first.get("invoice_id") != second.get("invoice_id")
                and _vendor_key(first["vendor"]) == _vendor_key(second["vendor"])
                and first_amount == second_amount
                and first.get("date") == second.get("date")
            ):
                suspected_duplicates.append(
                    {
                        "invoice_ids": [
                            first.get("invoice_id"),
                            second.get("invoice_id"),
                        ],
                        "indexes": [first_index, second_index],
                    }
                )

    parsed_dates = []
    for index, invoice in enumerate(invoices):
        try:
            parsed_dates.append(Date.fromisoformat(invoice.get("date")))
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"Invoice at index {index} has an invalid or missing ISO date."
            ) from error

    positive_candidates = {}
    for index, invoice in enumerate(invoices):
        amount = _numeric_amount(invoice)
        if amount is not None and amount > 0:
            key = (_vendor_key(invoice["vendor"]), amount)
            positive_candidates.setdefault(key, []).append(index)

    matched_positives = set()
    credit_note_pairs = []
    unmatched_credit_note_rows = []
    for credit_index, credit in enumerate(invoices):
        amount = _numeric_amount(credit)
        if amount is None or amount >= 0:
            continue
        key = (_vendor_key(credit["vendor"]), abs(amount))
        candidates = [
            index
            for index in positive_candidates.get(key, [])
            if index not in matched_positives and parsed_dates[index] < parsed_dates[credit_index]
        ]
        if not candidates:
            unmatched_credit_note_rows.append(credit_index)
            continue

        positive_index = max(candidates, key=lambda index: parsed_dates[index])
        matched_positives.add(positive_index)
        invoices[credit_index]["status"] = "CANCELLED"
        invoices[positive_index]["status"] = "CANCELLED"
        credit_note_pairs.append((positive_index, credit_index))

    cancelled_indexes = {
        index
        for pair in credit_note_pairs
        for index in pair
    }

    payments_by_invoice = {}
    for payment in payments:
        payment_model = Payment(**payment)
        payments_by_invoice[payment_model.invoice_id] = (
            payments_by_invoice.get(payment_model.invoice_id, 0) + payment_model.paid
        )

    invoice_ids = {invoice.get("invoice_id") for invoice in invoices}
    unmatched_payments = sorted(set(payments_by_invoice) - invoice_ids)
    payment_reconciliation = []
    vendor_totals = {}
    invoice_total = 0
    paid_total = 0
    for index, invoice in enumerate(invoices):
        amount = _numeric_amount(invoice)
        if amount is None or index in cancelled_indexes:
            continue
        invoice_id = invoice.get("invoice_id")
        paid = payments_by_invoice.get(invoice_id, 0)
        invoice_total += amount
        paid_total += paid
        vendor = invoice["vendor"]
        vendor_totals[vendor] = vendor_totals.get(vendor, 0) + amount
        payment_reconciliation.append(
            {
                "invoice_id": invoice_id,
                "amount": amount,
                "paid": paid,
                "balance": amount - paid,
            }
        )

    report = {
        "missing_amount_rows": missing_amount_rows,
        "exact_dupes": exact_dupes,
        "removed_duplicate_rows": sorted(duplicate_indexes),
        "suspected_duplicates": suspected_duplicates,
        "credit_note_pairs": credit_note_pairs,
        "unmatched_credit_note_rows": unmatched_credit_note_rows,
        "vendor_totals": vendor_totals,
        "payment_reconciliation": payment_reconciliation,
        "invoice_total": invoice_total,
        "paid_total": paid_total,
        "balance_total": invoice_total - paid_total,
        "unmatched_payment_invoice_ids": unmatched_payments,
    }
    _print_report(report)
    return report


def process_invoices() -> dict:
    invoices = repository.load_invoices()
    payments = repository.load_payments()
    report = process_invoice_rows(invoices, payments)
    repository.save_invoices(invoices)
    return report


def reconcile_payments() -> dict:
    invoices = repository.load_invoices()
    payments = repository.load_payments()
    payments_by_invoice = {}
    for payment in payments:
        parsed_payment = Payment(**payment)
        payments_by_invoice[parsed_payment.invoice_id] = (
            payments_by_invoice.get(parsed_payment.invoice_id, 0) + parsed_payment.paid
        )

    reconciled = []
    invoice_total = 0
    paid_total = 0
    for invoice in invoices:
        amount = _numeric_amount(invoice)
        if amount is None or invoice.get("status") == "CANCELLED":
            continue
        paid = payments_by_invoice.get(invoice["invoice_id"], 0)
        invoice_total += amount
        paid_total += paid
        reconciled.append(
            {
                "invoice_id": invoice["invoice_id"],
                "amount": amount,
                "paid": paid,
                "balance": amount - paid,
            }
        )
    return {
        "invoices": reconciled,
        "invoice_total": invoice_total,
        "paid_total": paid_total,
        "balance_total": invoice_total - paid_total,
    }


def list_payments(invoice_id: str | None = None) -> list[dict]:
    payments = repository.load_payments()
    if invoice_id is None:
        return payments
    return [payment for payment in payments if payment.get("invoice_id") == invoice_id]


def get_payment(payment_index: int) -> Payment:
    payment = repository.find_payment_by_index(payment_index)
    if payment is None:
        raise ValueError(f"Payment at index {payment_index} not found.")
    return Payment(**payment)


def create_payment(payment_data: dict) -> Payment:
    payment = Payment(**payment_data)
    if repository.find_invoice_by_id(payment.invoice_id) is None:
        raise ValueError(f"Invoice {payment.invoice_id} not found.")
    repository.add_payment(payment.model_dump())
    return payment


def update_payment(payment_index: int, payment_data: dict) -> Payment:
    payment = Payment(**payment_data)
    if repository.find_invoice_by_id(payment.invoice_id) is None:
        raise ValueError(f"Invoice {payment.invoice_id} not found.")
    if not repository.update_payment(payment_index, payment.model_dump()):
        raise ValueError(f"Payment at index {payment_index} not found.")
    return payment


def delete_payment(payment_index: int) -> None:
    if not repository.delete_payment(payment_index):
        raise ValueError(f"Payment at index {payment_index} not found.")


def get_invoice(invoice_id: str) -> Invoice:
    invoice_data = repository.find_invoice_by_id(invoice_id)
    if invoice_data is None:
        raise ValueError(f"Invoice with ID {invoice_id} not found.")
    return Invoice(**invoice_data)

def create_invoice(invoice_data: dict) -> Invoice:
    new_invoice = Invoice(**invoice_data)
    repository.add_invoice(new_invoice.model_dump())
    return new_invoice

def update_invoice(invoice_id: str, updated_data: dict) -> Invoice:
    existing_invoice = repository.find_invoice_by_id(invoice_id)
    if existing_invoice is None:
        raise ValueError(f"Invoice with ID {invoice_id} not found.")
    
    updated_invoice = Invoice(**{**existing_invoice, **updated_data})
    repository.update_invoice(invoice_id, updated_invoice.model_dump())
    return updated_invoice

def delete_invoice(invoice_id: str) -> None:
    existing_invoice = repository.find_invoice_by_id(invoice_id)
    if existing_invoice is None:
        raise ValueError(f"Invoice with ID {invoice_id} not found.")
    
    repository.delete_invoice(invoice_id)