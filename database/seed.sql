
INSERT INTO documents (document_id, filename, document_type, status)
VALUES
    ('invoice_sample', 'invoice_sample.txt', 'INVOICE', 'UPLOADED'),
    ('contract_sample', 'contract_sample.txt', 'CONTRACT', 'UPLOADED')
ON CONFLICT (document_id) DO NOTHING;

INSERT INTO extracted_fields (document_id, fields)
VALUES
    ('invoice_sample', '{
        "vendor": "ABC Corp",
        "invoice_number": "INV-1024",
        "total": 15000,
        "currency": "EGP",
        "due_date": "2026-09-01"
    }'::jsonb),
    ('contract_sample', '{
        "parties": ["Company A", "Company B"],
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "payment_terms": "60 days"
    }'::jsonb)
ON CONFLICT (document_id) DO NOTHING;

INSERT INTO risk_assessments (document_id, risk_score, financial_risk, legal_risk, operational_risk, risk_reasons)
VALUES
    ('contract_sample', 72, 'High', 'Medium', 'High', '[
        "Automatic renewal detected (Section 4)",
        "Short termination notice period for cause (15 days)",
        "Liability cap tied to trailing 12 months of fees only"
    ]'::jsonb)
ON CONFLICT (document_id) DO NOTHING;
