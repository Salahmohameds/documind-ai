"""Shared fixtures for ai-service contract tests.

Start a local instance:

    cd services/ai-service
    AI_BACKEND=mock uvicorn app.main:app --port 8083

The mock backend is rules-based, not random — classification, extraction,
PII and risk all run real deterministic logic. That makes it worth
testing behaviour, not just response shape. Generation quality still
needs a real provider.
"""

import os

import httpx
import pytest

BASE_URL = os.environ.get("AI_SERVICE_URL", "http://127.0.0.1:8083")
TIMEOUT = float(os.environ.get("AI_SERVICE_TIMEOUT", "30"))


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=BASE_URL.rstrip("/"), timeout=TIMEOUT) as c:
        try:
            c.get("/liveness")
        except httpx.ConnectError:
            pytest.skip(
                f"no ai-service at {BASE_URL} — "
                "set AI_SERVICE_URL or start a local instance"
            )
        yield c


@pytest.fixture(scope="session")
def invoice_text():
    return (
        "INVOICE\n"
        "Invoice number: INV-1024\n"
        "Vendor: ABC Corp\n"
        "Total due: 15,000 EGP\n"
        "Due date: 2026-09-01\n"
    )


@pytest.fixture(scope="session")
def contract_text():
    return (
        "SERVICE AGREEMENT\n"
        "This Agreement is entered into between Company A and Company B.\n"
        "This Agreement renews automatically for successive one-year terms.\n"
        "Either party may terminate for cause upon 15 days written notice.\n"
        "Total liability shall not exceed fees paid in the 6 months "
        "preceding the claim.\n"
        "Payment is due within 60 days of receipt of a valid invoice.\n"
    )