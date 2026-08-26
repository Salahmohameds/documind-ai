"""Seed data and PII generation for the synthetic corpus.

Every value here is chosen so the generator can build a document FROM
the ground truth, guaranteeing the expected values are correct by
construction rather than by transcription.
"""

import random

COMPANIES = [
    "Nile Systems LLC", "Delta Trading Co", "Cairo Cloud Partners",
    "Alexandria Logistics", "Horus Technologies", "Sphinx Analytics",
    "Red Sea Consulting", "Giza Data Works", "Luxor Software House",
    "Aswan Industrial Group", "Sinai Freight Services", "Fayoum Agritech",
    "Suez Marine Supply", "Minya Textiles", "Damietta Furniture Export",
    "Port Said Shipping", "Tanta Pharma Distribution", "Zagazig Foods",
    "Ismailia Engineering", "Beni Suef Cement",
]

CURRENCIES = ["EGP", "USD", "EUR"]

PAYMENT_TERM_DAYS = [15, 30, 45, 60, 90]

SERVICES = [
    "cloud infrastructure consulting",
    "document intelligence platform development",
    "Kubernetes deployment support",
    "data migration services",
    "security architecture review",
    "managed database administration",
    "API integration engineering",
    "disaster recovery planning",
]

GOVERNING_LAW = [
    "the laws of the Arab Republic of Egypt",
    "the laws specified in Exhibit C",
    "the laws of the Emirate of Dubai",
]


def _slug(company):
    return company.split()[0].lower()


def make_pii(rng, company, page_map):
    """Build a PII set. page_map tells us which page each type lands on.

    Values use .example / documentation-reserved ranges so nothing here
    can collide with a real person or a real account.
    """
    domain = f"{_slug(company)}.example"
    entities = [
        {
            "type": "EMAIL",
            "value": f"{rng.choice(['ops', 'billing', 'legal', 'contracts'])}@{domain}",
            "page": page_map["EMAIL"],
        },
        {
            "type": "PHONE",
            "value": f"+20 10{rng.randint(0, 9)} 555 {rng.randint(1000, 9999)}",
            "page": page_map["PHONE"],
        },
        {
            "type": "NATIONAL_ID",
            "value": "".join(str(rng.randint(0, 9)) for _ in range(14)),
            "page": page_map["NATIONAL_ID"],
        },
        {
            "type": "BANK_ACCOUNT",
            "value": f"EG{rng.randint(10, 99)} {rng.randint(1000, 9999)} "
                     f"{rng.randint(1000, 9999)} {rng.randint(1000, 9999)}",
            "page": page_map["BANK_ACCOUNT"],
        },
        {
            "type": "ADDRESS",
            "value": f"{rng.randint(1, 200)} {rng.choice(['Tahrir', 'Corniche', 'Ramses', 'Gomhoria'])} "
                     f"Street, {rng.choice(['Cairo', 'Alexandria', 'Giza', 'Banha'])}, Egypt",
            "page": page_map["ADDRESS"],
        },
    ]
    return entities


def new_rng(seed):
    """One RNG per document, seeded from the document index.

    This makes the whole corpus reproducible: regenerating with the same
    seed produces byte-identical documents, so a metric change always
    means a code change, never a corpus change.
    """
    return random.Random(seed)