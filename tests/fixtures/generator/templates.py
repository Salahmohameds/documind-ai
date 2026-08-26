"""Document body builders.

Each builder returns (pages, ground_truth). `pages` is a list of lists of
lines — one inner list per page — so page numbers in the ground truth are
assigned by construction, not guessed after rendering.
"""

from datetime import date, timedelta

from data import (
    COMPANIES, CURRENCIES, GOVERNING_LAW, PAYMENT_TERM_DAYS, SERVICES,
    make_pii,
)


def _date(rng, start_year=2026):
    start = date(start_year, 1, 1) + timedelta(days=rng.randint(0, 300))
    return start


def _money(rng, low, high):
    return rng.randrange(low, high, 500)


# ─────────────────────────── CONTRACT ───────────────────────────

def build_contract(rng, doc_id):
    provider, client = rng.sample(COMPANIES, 2)
    start = _date(rng)
    end = start + timedelta(days=365)
    terms = rng.choice(PAYMENT_TERM_DAYS)
    currency = rng.choice(CURRENCIES)
    total = _money(rng, 20000, 500000)
    scope = rng.sample(SERVICES, 3)
    law = rng.choice(GOVERNING_LAW)

    # Risk drivers — chosen first, then written into the text.
    auto_renewal = rng.random() < 0.55
    termination_days = rng.choice([15, 30, 60, 90])
    liability_multiple = rng.choice([6, 12, 24])
    late_interest = rng.choice([1.0, 1.5, 2.0])

    pii = make_pii(rng, provider, {
        "EMAIL": 1, "PHONE": 1, "ADDRESS": 1,
        "BANK_ACCOUNT": 2, "NATIONAL_ID": 4,
    })
    by_type = {p["type"]: p["value"] for p in pii}

    p1 = [
        "SERVICE AGREEMENT",
        "",
        f"This Service Agreement is entered into between {provider} "
        f'(the "Provider") and {client} (the "Client").',
        "",
        "1. PARTIES",
        f"Provider: {provider}",
        f"Registered address: {by_type['ADDRESS']}",
        f"Contact email: {by_type['EMAIL']}",
        f"Contact telephone: {by_type['PHONE']}",
        f"Client: {client}",
        "",
        "2. TERM",
        f"This Agreement commences on {start.isoformat()} and remains in "
        f"effect until {end.isoformat()}.",
        "",
        "3. SCOPE OF SERVICES",
        "The Provider shall deliver the following services as further "
        "described in Exhibit A:",
    ] + [f"   - {s.capitalize()}." for s in scope]

    p2 = [
        "4. FEES AND PAYMENT",
        f"The total contract value is {total:,} {currency}.",
        f"Payment is due within {terms} days of receipt of a valid invoice.",
        f"Late payments accrue interest at {late_interest}% per month.",
        "",
        "Remittance details:",
        f"Account: {by_type['BANK_ACCOUNT']}",
        "",
        "5. RENEWAL",
    ]
    if auto_renewal:
        p2 += [
            "This Agreement renews automatically for successive one-year "
            "terms unless either party provides 30 days written notice of "
            "non-renewal prior to the end of the then-current term.",
        ]
    else:
        p2 += [
            "This Agreement does not renew automatically. Any extension "
            "requires a written amendment signed by both parties.",
        ]

    p3 = [
        "6. TERMINATION",
        f"Either party may terminate this Agreement for cause upon "
        f"{termination_days} days written notice, subject to a cure period.",
        "The Client may terminate for convenience upon 30 days written notice.",
        "",
        "7. LIMITATION OF LIABILITY",
        f"Total liability shall not exceed the total fees paid by the Client "
        f"in the {liability_multiple} months preceding the claim.",
        "Neither party is liable for indirect, incidental, or consequential "
        "damages.",
    ]

    p4 = [
        "8. CONFIDENTIALITY",
        "Each party shall protect the other's confidential information for "
        "two years following termination of this Agreement.",
        "",
        "9. GOVERNING LAW",
        f"This Agreement is governed by {law}.",
        "",
        "10. SIGNATURES",
        f"Authorised signatory national ID: {by_type['NATIONAL_ID']}",
        f"Executed on {start.isoformat()}.",
    ]

    # Risk band derived from the drivers above — deterministic, explainable.
    flags = []
    if auto_renewal:
        flags.append("auto_renewal")
    if termination_days <= 15:
        flags.append("short_termination_notice")
    if liability_multiple <= 6:
        flags.append("low_liability_cap")
    if total >= 250000:
        flags.append("high_contract_value")
    if late_interest >= 2.0:
        flags.append("high_late_interest")

    band = "LOW" if len(flags) <= 1 else "MEDIUM" if len(flags) <= 3 else "HIGH"

    ground_truth = {
        "document_id": doc_id,
        "filename": f"{doc_id}.pdf",
        "expected_type": "CONTRACT",
        "page_count": 4,
        "expected_fields": {
            "parties": [provider, client],
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "payment_terms": f"{terms} days",
            "total_value": total,
            "currency": currency,
        },
        "expected_pii": pii,
        "expected_risk": {"band": band, "flags": flags},
        "rag_questions": [
            {
                "question": "What are the payment terms?",
                "expected_answer": f"Payment is due within {terms} days of "
                                   f"receipt of a valid invoice.",
                "expected_page": 2,
            },
            {
                "question": "Does this contract renew automatically?",
                "expected_answer": (
                    "Yes, it renews automatically for successive one-year terms "
                    "unless either party gives 30 days written notice."
                    if auto_renewal else
                    "No, it does not renew automatically. Any extension requires "
                    "a written amendment."
                ),
                "expected_page": 2,
            },
            {
                "question": "How much notice is required to terminate for cause?",
                "expected_answer": f"{termination_days} days written notice, "
                                   f"subject to a cure period.",
                "expected_page": 3,
            },
            {
                "question": "What is the cap on liability?",
                "expected_answer": f"Total liability shall not exceed the fees "
                                   f"paid in the {liability_multiple} months "
                                   f"preceding the claim.",
                "expected_page": 3,
            },
            {
                "question": "Who are the parties to this agreement?",
                "expected_answer": f"{provider} (Provider) and {client} (Client).",
                "expected_page": 1,
            },
            {
                "question": "How long does confidentiality last after termination?",
                "expected_answer": "Two years following termination.",
                "expected_page": 4,
            },
        ],
    }

    return [p1, p2, p3, p4], ground_truth


# ─────────────────────────── INVOICE ───────────────────────────

def build_invoice(rng, doc_id):
    vendor, client = rng.sample(COMPANIES, 2)
    issued = _date(rng)
    net_days = rng.choice([15, 30, 45, 60])
    due = issued + timedelta(days=net_days)
    currency = rng.choice(CURRENCIES)
    number = f"INV-{rng.randint(1000, 9999)}"
    tax_rate = rng.choice([5, 7, 14])
    late_interest = rng.choice([1.0, 1.5, 2.0])

    items = []
    for s in rng.sample(SERVICES, rng.randint(2, 4)):
        amount = _money(rng, 2000, 60000)
        items.append((s.capitalize(), amount))

    subtotal = sum(a for _, a in items)
    tax = round(subtotal * tax_rate / 100)
    total = subtotal + tax

    pii = make_pii(rng, vendor, {
        "EMAIL": 1, "PHONE": 1, "ADDRESS": 1,
        "BANK_ACCOUNT": 1, "NATIONAL_ID": 1,
    })
    by_type = {p["type"]: p["value"] for p in pii}

    p1 = [
        "INVOICE",
        "",
        f"Invoice number: {number}",
        f"Issue date: {issued.isoformat()}",
        f"Due date: {due.isoformat()} (Net {net_days} days)",
        "",
        "FROM",
        vendor,
        by_type["ADDRESS"],
        f"Email: {by_type['EMAIL']}",
        f"Phone: {by_type['PHONE']}",
        f"Tax registration ID: {by_type['NATIONAL_ID']}",
        "",
        "BILL TO",
        client,
        "",
        "LINE ITEMS",
    ]
    for desc, amount in items:
        p1.append(f"   {desc:<52}{amount:>10,} {currency}")

    p1 += [
        "",
        f"   {'Subtotal':<52}{subtotal:>10,} {currency}",
        f"   {f'Tax ({tax_rate}%)':<52}{tax:>10,} {currency}",
        f"   {'TOTAL DUE':<52}{total:>10,} {currency}",
        "",
        "PAYMENT",
        f"Remit to account: {by_type['BANK_ACCOUNT']}",
        f"Payments received after {net_days} days accrue "
        f"{late_interest}% monthly interest.",
    ]

    ground_truth = {
        "document_id": doc_id,
        "filename": f"{doc_id}.pdf",
        "expected_type": "INVOICE",
        "page_count": 1,
        "expected_fields": {
            "vendor": vendor,
            "invoice_number": number,
            "total": total,
            "subtotal": subtotal,
            "tax": tax,
            "tax_rate": tax_rate,
            "currency": currency,
            "issue_date": issued.isoformat(),
            "due_date": due.isoformat(),
            "line_item_count": len(items),
        },
        "expected_pii": pii,
        "expected_risk": {"band": "LOW", "flags": []},
        "rag_questions": [
            {
                "question": "What is the total amount due?",
                "expected_answer": f"{total:,} {currency}.",
                "expected_page": 1,
            },
            {
                "question": "Who is the vendor?",
                "expected_answer": f"{vendor}.",
                "expected_page": 1,
            },
            {
                "question": "What is the invoice number?",
                "expected_answer": f"{number}.",
                "expected_page": 1,
            },
            {
                "question": "When is the invoice due?",
                "expected_answer": f"{due.isoformat()}, Net {net_days} days "
                                   f"from the issue date.",
                "expected_page": 1,
            },
            {
                "question": "What tax was applied?",
                "expected_answer": f"{tax_rate}% tax, amounting to "
                                   f"{tax:,} {currency}.",
                "expected_page": 1,
            },
        ],
    }

    return [p1], ground_truth