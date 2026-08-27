-- Demo dataset: a document library with enough variety to exercise the UI.
--
-- database/seed.sql is the minimal fixture the schema ships with (two rows).
-- This file is the richer one: realistic filenames, every lifecycle state, and
-- a risk distribution spread across all three bands so the dashboard dial,
-- the verdict split and the findings list all have something real to render.
--
-- Idempotent -- re-running it refreshes the analysis rather than duplicating
-- documents. Apply with:
--   docker exec -i documind-postgres psql -U documind -d documind < database/seed_demo.sql
--
-- Three fields the UI shows are NOT set from here because document-service
-- hardcodes them in `_summary` (services/document-service/app/services/
-- documents.py): `pages` is always 0, `counterparty` is always "Unassigned
-- counterparty", and `pii` is always empty because nothing writes it. Seeding
-- cannot move them; that needs a service change.

BEGIN;

INSERT INTO documents (document_id, filename, document_type, status, uploaded_at, indexed_at)
VALUES
    ('doc_54a7dc8c15940f54fc2a64d1de84daa3', 'MSA_TransGlobal_2026_full_execution_copy_final.pdf', 'CONTRACT', 'INDEXED', '2026-08-27T16:04:27.358297+00:00', '2026-08-27T16:04:57.358297+00:00'),
    ('doc_81671ec6b5356c0d5fce35a01ee82e8c', 'Global_MSA_Amendment_2.pdf', 'CONTRACT', 'INDEXED', '2026-08-27T12:52:27.358297+00:00', '2026-08-27T12:53:17.358297+00:00'),
    ('doc_a0a9abdbb05e2184e56ebe4602caa818', 'Framework_Agreement_Perrin.pdf', 'CONTRACT', 'INDEXED', '2026-08-27T08:44:27.358297+00:00', '2026-08-27T08:45:07.358297+00:00'),
    ('doc_ac3d7a1f747a0dc72525655a3bd710b9', 'MSA_Sable_Transport_2025.pdf', 'CONTRACT', 'INDEXED', '2026-08-27T03:55:27.358297+00:00', '2026-08-27T03:56:37.358297+00:00'),
    ('doc_b56316a70164e265b93850d9641a02a6', 'Amendment_1_Halcyon_SLA.pdf', 'CONTRACT', 'INDEXED', '2026-08-26T22:02:27.358297+00:00', '2026-08-26T22:05:17.358297+00:00'),
    ('doc_9b06d5606f0b831865ac3fb2eaf0e889', 'Vendor_NDA_Kestrel_v4.pdf', 'CONTRACT', 'INDEXED', '2026-08-26T16:14:27.358297+00:00', '2026-08-26T16:17:07.358297+00:00'),
    ('doc_d66d11ac0359344a357b9a88ad388b4e', 'INV-2026-04398_Cardinal.pdf', 'INVOICE', 'INDEXED', '2026-08-26T12:10:27.358297+00:00', '2026-08-26T12:13:27.358297+00:00'),
    ('doc_05219d93574e8e2e1303fe085ff2ac7c', 'NDA_Pacific_Cargo_2026.pdf', 'CONTRACT', 'INDEXED', '2026-08-26T08:09:27.358297+00:00', '2026-08-26T08:09:57.358297+00:00'),
    ('doc_17e252c2b07594ab8e0c7fd0ab810acd', 'INV-2026-04344_TransGlobal.pdf', 'INVOICE', 'INDEXED', '2026-08-26T03:57:27.358297+00:00', '2026-08-26T03:58:07.358297+00:00'),
    ('doc_322c5345b1f1a85b199268991e8817f6', 'SOW_Ridgeline_Consulting.pdf', 'CONTRACT', 'INDEXED', '2026-08-25T22:19:27.358297+00:00', '2026-08-25T22:21:07.358297+00:00'),
    ('doc_7d8a7777a894c67e2c4f82322f0d38cd', 'INV-2026-04287_Cardinal.pdf', 'INVOICE', 'INDEXED', '2026-08-25T16:27:27.358297+00:00', '2026-08-25T16:29:17.358297+00:00'),
    ('doc_289cfb3aa14ac20f24e83b492a1f984f', 'Amendment_2_Kestrel_Term.pdf', 'CONTRACT', 'INDEXED', '2026-08-25T11:10:27.358297+00:00', '2026-08-25T11:13:27.358297+00:00'),
    ('doc_f392713ab1d3ce8472d4ae6916dbb6bd', 'Statement_AUG_Northwind.pdf', 'INVOICE', 'INDEXED', '2026-08-25T04:51:27.358297+00:00', '2026-08-25T04:53:47.358297+00:00'),
    ('doc_9f52e08babc93b64c58e3b8dad8db9fe', 'INV-2026-04360_Meridian_Rail.pdf', 'INVOICE', 'INDEXED', '2026-08-24T22:52:27.358297+00:00', '2026-08-24T22:54:07.358297+00:00'),
    ('doc_793eae13b4e7fe07d5aeb3ad3b072f33', 'NDA_Midwest_Haulers_v2.pdf', 'CONTRACT', 'INDEXED', '2026-08-24T17:46:27.358297+00:00', '2026-08-24T17:49:47.358297+00:00'),
    ('doc_1fbeb044f4939a6dcd83ba9735995f0e', 'ACME_Q3_MSA_countersigned.pdf', 'CONTRACT', 'INDEXED', '2026-08-24T12:12:27.358297+00:00', '2026-08-24T12:13:17.358297+00:00'),
    ('doc_5e63340ef6e93f86d234471bb8ecb9db', 'INV-2026-04385_Atlas.pdf', 'INVOICE', 'INDEXED', '2026-08-24T05:47:27.358297+00:00', '2026-08-24T05:50:07.358297+00:00'),
    ('doc_7715cccb66d226f435b644714c8984e9', 'INV-2026-04417_Northwind.pdf', 'INVOICE', 'INDEXED', '2026-08-24T00:15:27.358297+00:00', '2026-08-24T00:17:27.358297+00:00'),
    ('doc_5741a34ea0146a3ee5a5f98f53beb9f1', 'INV-2026-04271_Northwind.pdf', 'INVOICE', 'INDEXED', '2026-08-23T18:28:27.358297+00:00', '2026-08-23T18:29:37.358297+00:00'),
    ('doc_8f5f64c5ab9e793985e569ff8dd574b0', 'INV-2026-04331_Midwest.pdf', 'INVOICE', 'INDEXED', '2026-08-23T10:53:27.358297+00:00', '2026-08-23T10:54:27.358297+00:00'),
    ('doc_e832a419ae7f531a19faed3ba4025c08', 'Master_Services_Baltic.pdf', 'CONTRACT', 'PROCESSING', '2026-08-27T17:05:27.358297+00:00', NULL),
    ('doc_07faffdae0ac575362ff837744fefa37', 'Amendment_3_Atlas_Rates.pdf', 'CONTRACT', 'PROCESSING', '2026-08-27T17:04:27.358297+00:00', NULL),
    ('doc_6dfe99b4fa903469f77b007e5bc930e2', 'INV-2026-04409_Perrin.pdf', 'INVOICE', 'UPLOADED', '2026-08-27T18:22:27.358297+00:00', NULL),
    ('doc_1ce209d1db5f59c1602697496910077f', 'INV-2026-04298_Pacific.pdf', 'UNKNOWN', 'UPLOADED', '2026-08-27T18:10:27.358297+00:00', NULL),
    ('doc_94d17de44647548975fbbfc8ae36f8e8', 'INV-2026-04416_Halcyon.pdf', 'INVOICE', 'FAILED', '2026-08-27T10:50:27.358297+00:00', NULL),
    ('doc_77e33b10343748c7ccd5a65f987bfe3d', 'Statement_JUL_Baltic.pdf', 'UNKNOWN', 'FAILED', '2026-08-27T06:28:27.358297+00:00', NULL)
ON CONFLICT (document_id) DO UPDATE SET
    filename = EXCLUDED.filename,
    document_type = EXCLUDED.document_type,
    status = EXCLUDED.status,
    uploaded_at = EXCLUDED.uploaded_at,
    indexed_at = EXCLUDED.indexed_at;

INSERT INTO extracted_fields (document_id, fields)
VALUES
    ('doc_54a7dc8c15940f54fc2a64d1de84daa3', $j${
        "parties": {
                "value": "Meridian Logistics LLC; TransGlobal Inc.",
                "confidence": 0.97,
                "evidence": {
                        "page": 1
                }
        },
        "effective_date": {
                "value": "2026-01-15",
                "confidence": 0.94,
                "evidence": {
                        "page": 1
                }
        },
        "term_length": {
                "value": "36 months",
                "confidence": 0.91,
                "evidence": {
                        "page": 2
                }
        },
        "renewal_type": {
                "value": "Automatic",
                "confidence": 0.88,
                "evidence": {
                        "page": 4
                }
        },
        "notice_period_days": {
                "value": "15",
                "confidence": 0.86,
                "evidence": {
                        "page": 4
                }
        },
        "governing_law": {
                "value": "State of New York",
                "confidence": 0.93,
                "evidence": {
                        "page": 11
                }
        },
        "liability_cap": {
                "value": "Trailing 12 months of fees",
                "confidence": 0.79,
                "evidence": {
                        "page": 9
                }
        },
        "payment_terms": {
                "value": "Net 60",
                "confidence": 0.92,
                "evidence": {
                        "page": 6
                }
        },
        "termination_for_convenience": {
                "value": "Not permitted",
                "confidence": 0.81,
                "evidence": {
                        "page": 8
                }
        },
        "indemnity_scope": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        },
        "assignment_clause": {
                "value": "Consent required",
                "confidence": 0.74,
                "evidence": {
                        "page": 10
                }
        }
}$j$::jsonb),
    ('doc_81671ec6b5356c0d5fce35a01ee82e8c', $j${
        "parties": {
                "value": "Meridian Logistics LLC; Acme Freight Holdings",
                "confidence": 0.97,
                "evidence": {
                        "page": 1
                }
        },
        "effective_date": {
                "value": "2026-01-15",
                "confidence": 0.94,
                "evidence": {
                        "page": 1
                }
        },
        "term_length": {
                "value": "36 months",
                "confidence": 0.91,
                "evidence": {
                        "page": 2
                }
        },
        "renewal_type": {
                "value": "Automatic",
                "confidence": 0.88,
                "evidence": {
                        "page": 4
                }
        },
        "notice_period_days": {
                "value": "15",
                "confidence": 0.86,
                "evidence": {
                        "page": 4
                }
        },
        "governing_law": {
                "value": "State of New York",
                "confidence": 0.93,
                "evidence": {
                        "page": 11
                }
        },
        "liability_cap": {
                "value": "Trailing 12 months of fees",
                "confidence": 0.79,
                "evidence": {
                        "page": 9
                }
        },
        "payment_terms": {
                "value": "Net 60",
                "confidence": 0.92,
                "evidence": {
                        "page": 6
                }
        },
        "termination_for_convenience": {
                "value": "Not permitted",
                "confidence": 0.81,
                "evidence": {
                        "page": 8
                }
        },
        "indemnity_scope": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        },
        "assignment_clause": {
                "value": "Consent required",
                "confidence": 0.74,
                "evidence": {
                        "page": 10
                }
        }
}$j$::jsonb),
    ('doc_a0a9abdbb05e2184e56ebe4602caa818', $j${
        "parties": {
                "value": "Meridian Logistics LLC; Perrin & Co.",
                "confidence": 0.97,
                "evidence": {
                        "page": 1
                }
        },
        "effective_date": {
                "value": "2026-01-15",
                "confidence": 0.94,
                "evidence": {
                        "page": 1
                }
        },
        "term_length": {
                "value": "36 months",
                "confidence": 0.91,
                "evidence": {
                        "page": 2
                }
        },
        "renewal_type": {
                "value": "Automatic",
                "confidence": 0.88,
                "evidence": {
                        "page": 4
                }
        },
        "notice_period_days": {
                "value": "15",
                "confidence": 0.86,
                "evidence": {
                        "page": 4
                }
        },
        "governing_law": {
                "value": "State of New York",
                "confidence": 0.93,
                "evidence": {
                        "page": 11
                }
        },
        "liability_cap": {
                "value": "Trailing 12 months of fees",
                "confidence": 0.79,
                "evidence": {
                        "page": 9
                }
        },
        "payment_terms": {
                "value": "Net 60",
                "confidence": 0.92,
                "evidence": {
                        "page": 6
                }
        },
        "termination_for_convenience": {
                "value": "Not permitted",
                "confidence": 0.81,
                "evidence": {
                        "page": 8
                }
        },
        "indemnity_scope": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        },
        "assignment_clause": {
                "value": "Consent required",
                "confidence": 0.74,
                "evidence": {
                        "page": 10
                }
        }
}$j$::jsonb),
    ('doc_ac3d7a1f747a0dc72525655a3bd710b9', $j${
        "parties": {
                "value": "Meridian Logistics LLC; Sable Transport",
                "confidence": 0.97,
                "evidence": {
                        "page": 1
                }
        },
        "effective_date": {
                "value": "2026-01-15",
                "confidence": 0.94,
                "evidence": {
                        "page": 1
                }
        },
        "term_length": {
                "value": "36 months",
                "confidence": 0.91,
                "evidence": {
                        "page": 2
                }
        },
        "renewal_type": {
                "value": "Automatic",
                "confidence": 0.88,
                "evidence": {
                        "page": 4
                }
        },
        "notice_period_days": {
                "value": "15",
                "confidence": 0.86,
                "evidence": {
                        "page": 4
                }
        },
        "governing_law": {
                "value": "State of New York",
                "confidence": 0.93,
                "evidence": {
                        "page": 11
                }
        },
        "liability_cap": {
                "value": "Trailing 12 months of fees",
                "confidence": 0.79,
                "evidence": {
                        "page": 9
                }
        },
        "payment_terms": {
                "value": "Net 60",
                "confidence": 0.92,
                "evidence": {
                        "page": 6
                }
        },
        "termination_for_convenience": {
                "value": "Not permitted",
                "confidence": 0.81,
                "evidence": {
                        "page": 8
                }
        },
        "indemnity_scope": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        },
        "assignment_clause": {
                "value": "Consent required",
                "confidence": 0.74,
                "evidence": {
                        "page": 10
                }
        }
}$j$::jsonb),
    ('doc_b56316a70164e265b93850d9641a02a6', $j${
        "parties": {
                "value": "Meridian Logistics LLC; Halcyon Shipping",
                "confidence": 0.97,
                "evidence": {
                        "page": 1
                }
        },
        "effective_date": {
                "value": "2026-01-15",
                "confidence": 0.94,
                "evidence": {
                        "page": 1
                }
        },
        "term_length": {
                "value": "36 months",
                "confidence": 0.91,
                "evidence": {
                        "page": 2
                }
        },
        "renewal_type": {
                "value": "Automatic",
                "confidence": 0.88,
                "evidence": {
                        "page": 4
                }
        },
        "notice_period_days": {
                "value": "15",
                "confidence": 0.86,
                "evidence": {
                        "page": 4
                }
        },
        "governing_law": {
                "value": "State of New York",
                "confidence": 0.93,
                "evidence": {
                        "page": 11
                }
        },
        "liability_cap": {
                "value": "Trailing 12 months of fees",
                "confidence": 0.79,
                "evidence": {
                        "page": 9
                }
        },
        "payment_terms": {
                "value": "Net 60",
                "confidence": 0.92,
                "evidence": {
                        "page": 6
                }
        },
        "termination_for_convenience": {
                "value": "Not permitted",
                "confidence": 0.81,
                "evidence": {
                        "page": 8
                }
        },
        "indemnity_scope": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        },
        "assignment_clause": {
                "value": "Consent required",
                "confidence": 0.74,
                "evidence": {
                        "page": 10
                }
        }
}$j$::jsonb),
    ('doc_9b06d5606f0b831865ac3fb2eaf0e889', $j${
        "parties": {
                "value": "Meridian Logistics LLC; Kestrel Systems",
                "confidence": 0.97,
                "evidence": {
                        "page": 1
                }
        },
        "effective_date": {
                "value": "2026-01-15",
                "confidence": 0.94,
                "evidence": {
                        "page": 1
                }
        },
        "term_length": {
                "value": "36 months",
                "confidence": 0.91,
                "evidence": {
                        "page": 2
                }
        },
        "renewal_type": {
                "value": "Automatic",
                "confidence": 0.88,
                "evidence": {
                        "page": 4
                }
        },
        "notice_period_days": {
                "value": "15",
                "confidence": 0.86,
                "evidence": {
                        "page": 4
                }
        },
        "governing_law": {
                "value": "State of New York",
                "confidence": 0.93,
                "evidence": {
                        "page": 11
                }
        },
        "liability_cap": {
                "value": "Trailing 12 months of fees",
                "confidence": 0.79,
                "evidence": {
                        "page": 9
                }
        },
        "payment_terms": {
                "value": "Net 60",
                "confidence": 0.92,
                "evidence": {
                        "page": 6
                }
        },
        "termination_for_convenience": {
                "value": "Not permitted",
                "confidence": 0.81,
                "evidence": {
                        "page": 8
                }
        },
        "indemnity_scope": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        },
        "assignment_clause": {
                "value": "Consent required",
                "confidence": 0.74,
                "evidence": {
                        "page": 10
                }
        }
}$j$::jsonb),
    ('doc_d66d11ac0359344a357b9a88ad388b4e', $j${
        "vendor": {
                "value": "Cardinal Logistics",
                "confidence": 0.98,
                "evidence": {
                        "page": 1
                }
        },
        "invoice_number": {
                "value": "INV-2026-04398",
                "confidence": 0.99,
                "evidence": {
                        "page": 1
                }
        },
        "invoice_date": {
                "value": "2026-08-14",
                "confidence": 0.95,
                "evidence": {
                        "page": 1
                }
        },
        "due_date": {
                "value": "2026-09-13",
                "confidence": 0.94,
                "evidence": {
                        "page": 1
                }
        },
        "subtotal": {
                "value": "47,218.00",
                "confidence": 0.96,
                "evidence": {
                        "page": 1
                }
        },
        "tax": {
                "value": "6,610.52",
                "confidence": 0.93,
                "evidence": {
                        "page": 1
                }
        },
        "total": {
                "value": "53,828.52",
                "confidence": 0.97,
                "evidence": {
                        "page": 1
                }
        },
        "currency": {
                "value": "USD",
                "confidence": 0.99,
                "evidence": {
                        "page": 1
                }
        },
        "payment_terms": {
                "value": "Net 30",
                "confidence": 0.9,
                "evidence": {
                        "page": 2
                }
        },
        "po_number": {
                "value": "PO-4458",
                "confidence": 0.84,
                "evidence": {
                        "page": 1
                }
        },
        "remit_to": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        }
}$j$::jsonb),
    ('doc_05219d93574e8e2e1303fe085ff2ac7c', $j${
        "parties": {
                "value": "Meridian Logistics LLC; Pacific Cargo Ltd.",
                "confidence": 0.97,
                "evidence": {
                        "page": 1
                }
        },
        "effective_date": {
                "value": "2026-01-15",
                "confidence": 0.94,
                "evidence": {
                        "page": 1
                }
        },
        "term_length": {
                "value": "12 months",
                "confidence": 0.91,
                "evidence": {
                        "page": 2
                }
        },
        "renewal_type": {
                "value": "Manual",
                "confidence": 0.88,
                "evidence": {
                        "page": 4
                }
        },
        "notice_period_days": {
                "value": "90",
                "confidence": 0.86,
                "evidence": {
                        "page": 4
                }
        },
        "governing_law": {
                "value": "State of Delaware",
                "confidence": 0.93,
                "evidence": {
                        "page": 11
                }
        },
        "liability_cap": {
                "value": "2x annual contract value",
                "confidence": 0.79,
                "evidence": {
                        "page": 9
                }
        },
        "payment_terms": {
                "value": "Net 30",
                "confidence": 0.92,
                "evidence": {
                        "page": 6
                }
        },
        "termination_for_convenience": {
                "value": "Permitted, 30 days",
                "confidence": 0.81,
                "evidence": {
                        "page": 8
                }
        },
        "indemnity_scope": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        },
        "assignment_clause": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        }
}$j$::jsonb),
    ('doc_17e252c2b07594ab8e0c7fd0ab810acd', $j${
        "vendor": {
                "value": "TransGlobal Inc.",
                "confidence": 0.98,
                "evidence": {
                        "page": 1
                }
        },
        "invoice_number": {
                "value": "INV-2026-04344",
                "confidence": 0.99,
                "evidence": {
                        "page": 1
                }
        },
        "invoice_date": {
                "value": "2026-08-14",
                "confidence": 0.95,
                "evidence": {
                        "page": 1
                }
        },
        "due_date": {
                "value": "2026-09-13",
                "confidence": 0.94,
                "evidence": {
                        "page": 1
                }
        },
        "subtotal": {
                "value": "37,715.00",
                "confidence": 0.96,
                "evidence": {
                        "page": 1
                }
        },
        "tax": {
                "value": "5,280.10",
                "confidence": 0.93,
                "evidence": {
                        "page": 1
                }
        },
        "total": {
                "value": "42,995.10",
                "confidence": 0.97,
                "evidence": {
                        "page": 1
                }
        },
        "currency": {
                "value": "USD",
                "confidence": 0.99,
                "evidence": {
                        "page": 1
                }
        },
        "payment_terms": {
                "value": "Net 30",
                "confidence": 0.9,
                "evidence": {
                        "page": 2
                }
        },
        "po_number": {
                "value": "PO-4445",
                "confidence": 0.84,
                "evidence": {
                        "page": 1
                }
        },
        "remit_to": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        }
}$j$::jsonb),
    ('doc_322c5345b1f1a85b199268991e8817f6', $j${
        "parties": {
                "value": "Meridian Logistics LLC; Ridgeline Consulting",
                "confidence": 0.97,
                "evidence": {
                        "page": 1
                }
        },
        "effective_date": {
                "value": "2026-01-15",
                "confidence": 0.94,
                "evidence": {
                        "page": 1
                }
        },
        "term_length": {
                "value": "12 months",
                "confidence": 0.91,
                "evidence": {
                        "page": 2
                }
        },
        "renewal_type": {
                "value": "Manual",
                "confidence": 0.88,
                "evidence": {
                        "page": 4
                }
        },
        "notice_period_days": {
                "value": "90",
                "confidence": 0.86,
                "evidence": {
                        "page": 4
                }
        },
        "governing_law": {
                "value": "State of Delaware",
                "confidence": 0.93,
                "evidence": {
                        "page": 11
                }
        },
        "liability_cap": {
                "value": "2x annual contract value",
                "confidence": 0.79,
                "evidence": {
                        "page": 9
                }
        },
        "payment_terms": {
                "value": "Net 30",
                "confidence": 0.92,
                "evidence": {
                        "page": 6
                }
        },
        "termination_for_convenience": {
                "value": "Permitted, 30 days",
                "confidence": 0.81,
                "evidence": {
                        "page": 8
                }
        },
        "indemnity_scope": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        },
        "assignment_clause": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        }
}$j$::jsonb),
    ('doc_7d8a7777a894c67e2c4f82322f0d38cd', $j${
        "vendor": {
                "value": "Cardinal Logistics",
                "confidence": 0.98,
                "evidence": {
                        "page": 1
                }
        },
        "invoice_number": {
                "value": "INV-2026-04287",
                "confidence": 0.99,
                "evidence": {
                        "page": 1
                }
        },
        "invoice_date": {
                "value": "2026-08-14",
                "confidence": 0.95,
                "evidence": {
                        "page": 1
                }
        },
        "due_date": {
                "value": "2026-09-13",
                "confidence": 0.94,
                "evidence": {
                        "page": 1
                }
        },
        "subtotal": {
                "value": "32,598.00",
                "confidence": 0.96,
                "evidence": {
                        "page": 1
                }
        },
        "tax": {
                "value": "4,563.72",
                "confidence": 0.93,
                "evidence": {
                        "page": 1
                }
        },
        "total": {
                "value": "37,161.72",
                "confidence": 0.97,
                "evidence": {
                        "page": 1
                }
        },
        "currency": {
                "value": "USD",
                "confidence": 0.99,
                "evidence": {
                        "page": 1
                }
        },
        "payment_terms": {
                "value": "Net 30",
                "confidence": 0.9,
                "evidence": {
                        "page": 2
                }
        },
        "po_number": {
                "value": "PO-4438",
                "confidence": 0.84,
                "evidence": {
                        "page": 1
                }
        },
        "remit_to": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        }
}$j$::jsonb),
    ('doc_289cfb3aa14ac20f24e83b492a1f984f', $j${
        "parties": {
                "value": "Meridian Logistics LLC; Kestrel Systems",
                "confidence": 0.97,
                "evidence": {
                        "page": 1
                }
        },
        "effective_date": {
                "value": "2026-01-15",
                "confidence": 0.94,
                "evidence": {
                        "page": 1
                }
        },
        "term_length": {
                "value": "12 months",
                "confidence": 0.91,
                "evidence": {
                        "page": 2
                }
        },
        "renewal_type": {
                "value": "Manual",
                "confidence": 0.88,
                "evidence": {
                        "page": 4
                }
        },
        "notice_period_days": {
                "value": "90",
                "confidence": 0.86,
                "evidence": {
                        "page": 4
                }
        },
        "governing_law": {
                "value": "State of Delaware",
                "confidence": 0.93,
                "evidence": {
                        "page": 11
                }
        },
        "liability_cap": {
                "value": "2x annual contract value",
                "confidence": 0.79,
                "evidence": {
                        "page": 9
                }
        },
        "payment_terms": {
                "value": "Net 30",
                "confidence": 0.92,
                "evidence": {
                        "page": 6
                }
        },
        "termination_for_convenience": {
                "value": "Permitted, 30 days",
                "confidence": 0.81,
                "evidence": {
                        "page": 8
                }
        },
        "indemnity_scope": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        },
        "assignment_clause": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        }
}$j$::jsonb),
    ('doc_f392713ab1d3ce8472d4ae6916dbb6bd', $j${
        "vendor": {
                "value": "Northwind Traders",
                "confidence": 0.98,
                "evidence": {
                        "page": 1
                }
        },
        "invoice_number": {
                "value": "Statement",
                "confidence": 0.99,
                "evidence": {
                        "page": 1
                }
        },
        "invoice_date": {
                "value": "2026-08-14",
                "confidence": 0.95,
                "evidence": {
                        "page": 1
                }
        },
        "due_date": {
                "value": "2026-09-13",
                "confidence": 0.94,
                "evidence": {
                        "page": 1
                }
        },
        "subtotal": {
                "value": "27,481.00",
                "confidence": 0.96,
                "evidence": {
                        "page": 1
                }
        },
        "tax": {
                "value": "3,847.34",
                "confidence": 0.93,
                "evidence": {
                        "page": 1
                }
        },
        "total": {
                "value": "31,328.34",
                "confidence": 0.97,
                "evidence": {
                        "page": 1
                }
        },
        "currency": {
                "value": "USD",
                "confidence": 0.99,
                "evidence": {
                        "page": 1
                }
        },
        "payment_terms": {
                "value": "Net 30",
                "confidence": 0.9,
                "evidence": {
                        "page": 2
                }
        },
        "po_number": {
                "value": "PO-4431",
                "confidence": 0.84,
                "evidence": {
                        "page": 1
                }
        },
        "remit_to": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        }
}$j$::jsonb),
    ('doc_9f52e08babc93b64c58e3b8dad8db9fe', $j${
        "vendor": {
                "value": "Meridian Rail",
                "confidence": 0.98,
                "evidence": {
                        "page": 1
                }
        },
        "invoice_number": {
                "value": "INV-2026-04360",
                "confidence": 0.99,
                "evidence": {
                        "page": 1
                }
        },
        "invoice_date": {
                "value": "2026-08-14",
                "confidence": 0.95,
                "evidence": {
                        "page": 1
                }
        },
        "due_date": {
                "value": "2026-09-13",
                "confidence": 0.94,
                "evidence": {
                        "page": 1
                }
        },
        "subtotal": {
                "value": "26,019.00",
                "confidence": 0.96,
                "evidence": {
                        "page": 1
                }
        },
        "tax": {
                "value": "3,642.66",
                "confidence": 0.93,
                "evidence": {
                        "page": 1
                }
        },
        "total": {
                "value": "29,661.66",
                "confidence": 0.97,
                "evidence": {
                        "page": 1
                }
        },
        "currency": {
                "value": "USD",
                "confidence": 0.99,
                "evidence": {
                        "page": 1
                }
        },
        "payment_terms": {
                "value": "Net 30",
                "confidence": 0.9,
                "evidence": {
                        "page": 2
                }
        },
        "po_number": {
                "value": "PO-4429",
                "confidence": 0.84,
                "evidence": {
                        "page": 1
                }
        },
        "remit_to": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        }
}$j$::jsonb),
    ('doc_793eae13b4e7fe07d5aeb3ad3b072f33', $j${
        "parties": {
                "value": "Meridian Logistics LLC; Midwest Haulers",
                "confidence": 0.97,
                "evidence": {
                        "page": 1
                }
        },
        "effective_date": {
                "value": "2026-01-15",
                "confidence": 0.94,
                "evidence": {
                        "page": 1
                }
        },
        "term_length": {
                "value": "12 months",
                "confidence": 0.91,
                "evidence": {
                        "page": 2
                }
        },
        "renewal_type": {
                "value": "Manual",
                "confidence": 0.88,
                "evidence": {
                        "page": 4
                }
        },
        "notice_period_days": {
                "value": "90",
                "confidence": 0.86,
                "evidence": {
                        "page": 4
                }
        },
        "governing_law": {
                "value": "State of Delaware",
                "confidence": 0.93,
                "evidence": {
                        "page": 11
                }
        },
        "liability_cap": {
                "value": "2x annual contract value",
                "confidence": 0.79,
                "evidence": {
                        "page": 9
                }
        },
        "payment_terms": {
                "value": "Net 30",
                "confidence": 0.92,
                "evidence": {
                        "page": 6
                }
        },
        "termination_for_convenience": {
                "value": "Permitted, 30 days",
                "confidence": 0.81,
                "evidence": {
                        "page": 8
                }
        },
        "indemnity_scope": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        },
        "assignment_clause": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        }
}$j$::jsonb),
    ('doc_1fbeb044f4939a6dcd83ba9735995f0e', $j${
        "parties": {
                "value": "Meridian Logistics LLC; Acme Freight Holdings",
                "confidence": 0.97,
                "evidence": {
                        "page": 1
                }
        },
        "effective_date": {
                "value": "2026-01-15",
                "confidence": 0.94,
                "evidence": {
                        "page": 1
                }
        },
        "term_length": {
                "value": "12 months",
                "confidence": 0.91,
                "evidence": {
                        "page": 2
                }
        },
        "renewal_type": {
                "value": "Manual",
                "confidence": 0.88,
                "evidence": {
                        "page": 4
                }
        },
        "notice_period_days": {
                "value": "90",
                "confidence": 0.86,
                "evidence": {
                        "page": 4
                }
        },
        "governing_law": {
                "value": "State of Delaware",
                "confidence": 0.93,
                "evidence": {
                        "page": 11
                }
        },
        "liability_cap": {
                "value": "2x annual contract value",
                "confidence": 0.79,
                "evidence": {
                        "page": 9
                }
        },
        "payment_terms": {
                "value": "Net 30",
                "confidence": 0.92,
                "evidence": {
                        "page": 6
                }
        },
        "termination_for_convenience": {
                "value": "Permitted, 30 days",
                "confidence": 0.81,
                "evidence": {
                        "page": 8
                }
        },
        "indemnity_scope": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        },
        "assignment_clause": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        }
}$j$::jsonb),
    ('doc_5e63340ef6e93f86d234471bb8ecb9db', $j${
        "vendor": {
                "value": "Atlas Logistics",
                "confidence": 0.98,
                "evidence": {
                        "page": 1
                }
        },
        "invoice_number": {
                "value": "INV-2026-04385",
                "confidence": 0.99,
                "evidence": {
                        "page": 1
                }
        },
        "invoice_date": {
                "value": "2026-08-14",
                "confidence": 0.95,
                "evidence": {
                        "page": 1
                }
        },
        "due_date": {
                "value": "2026-09-13",
                "confidence": 0.94,
                "evidence": {
                        "page": 1
                }
        },
        "subtotal": {
                "value": "18,709.00",
                "confidence": 0.96,
                "evidence": {
                        "page": 1
                }
        },
        "tax": {
                "value": "2,619.26",
                "confidence": 0.93,
                "evidence": {
                        "page": 1
                }
        },
        "total": {
                "value": "21,328.26",
                "confidence": 0.97,
                "evidence": {
                        "page": 1
                }
        },
        "currency": {
                "value": "USD",
                "confidence": 0.99,
                "evidence": {
                        "page": 1
                }
        },
        "payment_terms": {
                "value": "Net 30",
                "confidence": 0.9,
                "evidence": {
                        "page": 2
                }
        },
        "po_number": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        },
        "remit_to": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        }
}$j$::jsonb),
    ('doc_7715cccb66d226f435b644714c8984e9', $j${
        "vendor": {
                "value": "Northwind Traders",
                "confidence": 0.98,
                "evidence": {
                        "page": 1
                }
        },
        "invoice_number": {
                "value": "INV-2026-04417",
                "confidence": 0.99,
                "evidence": {
                        "page": 1
                }
        },
        "invoice_date": {
                "value": "2026-08-14",
                "confidence": 0.95,
                "evidence": {
                        "page": 1
                }
        },
        "due_date": {
                "value": "2026-09-13",
                "confidence": 0.94,
                "evidence": {
                        "page": 1
                }
        },
        "subtotal": {
                "value": "15,785.00",
                "confidence": 0.96,
                "evidence": {
                        "page": 1
                }
        },
        "tax": {
                "value": "2,209.90",
                "confidence": 0.93,
                "evidence": {
                        "page": 1
                }
        },
        "total": {
                "value": "17,994.90",
                "confidence": 0.97,
                "evidence": {
                        "page": 1
                }
        },
        "currency": {
                "value": "USD",
                "confidence": 0.99,
                "evidence": {
                        "page": 1
                }
        },
        "payment_terms": {
                "value": "Net 30",
                "confidence": 0.9,
                "evidence": {
                        "page": 2
                }
        },
        "po_number": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        },
        "remit_to": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        }
}$j$::jsonb),
    ('doc_5741a34ea0146a3ee5a5f98f53beb9f1', $j${
        "vendor": {
                "value": "Northwind Traders",
                "confidence": 0.98,
                "evidence": {
                        "page": 1
                }
        },
        "invoice_number": {
                "value": "INV-2026-04271",
                "confidence": 0.99,
                "evidence": {
                        "page": 1
                }
        },
        "invoice_date": {
                "value": "2026-08-14",
                "confidence": 0.95,
                "evidence": {
                        "page": 1
                }
        },
        "due_date": {
                "value": "2026-09-13",
                "confidence": 0.94,
                "evidence": {
                        "page": 1
                }
        },
        "subtotal": {
                "value": "11,399.00",
                "confidence": 0.96,
                "evidence": {
                        "page": 1
                }
        },
        "tax": {
                "value": "1,595.86",
                "confidence": 0.93,
                "evidence": {
                        "page": 1
                }
        },
        "total": {
                "value": "12,994.86",
                "confidence": 0.97,
                "evidence": {
                        "page": 1
                }
        },
        "currency": {
                "value": "USD",
                "confidence": 0.99,
                "evidence": {
                        "page": 1
                }
        },
        "payment_terms": {
                "value": "Net 30",
                "confidence": 0.9,
                "evidence": {
                        "page": 2
                }
        },
        "po_number": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        },
        "remit_to": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        }
}$j$::jsonb),
    ('doc_8f5f64c5ab9e793985e569ff8dd574b0', $j${
        "vendor": {
                "value": "Midwest Haulers",
                "confidence": 0.98,
                "evidence": {
                        "page": 1
                }
        },
        "invoice_number": {
                "value": "INV-2026-04331",
                "confidence": 0.99,
                "evidence": {
                        "page": 1
                }
        },
        "invoice_date": {
                "value": "2026-08-14",
                "confidence": 0.95,
                "evidence": {
                        "page": 1
                }
        },
        "due_date": {
                "value": "2026-09-13",
                "confidence": 0.94,
                "evidence": {
                        "page": 1
                }
        },
        "subtotal": {
                "value": "9,937.00",
                "confidence": 0.96,
                "evidence": {
                        "page": 1
                }
        },
        "tax": {
                "value": "1,391.18",
                "confidence": 0.93,
                "evidence": {
                        "page": 1
                }
        },
        "total": {
                "value": "11,328.18",
                "confidence": 0.97,
                "evidence": {
                        "page": 1
                }
        },
        "currency": {
                "value": "USD",
                "confidence": 0.99,
                "evidence": {
                        "page": 1
                }
        },
        "payment_terms": {
                "value": "Net 30",
                "confidence": 0.9,
                "evidence": {
                        "page": 2
                }
        },
        "po_number": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        },
        "remit_to": {
                "value": null,
                "confidence": 0.0,
                "evidence": {
                        "page": null
                }
        }
}$j$::jsonb)
ON CONFLICT (document_id) DO UPDATE SET fields = EXCLUDED.fields;

INSERT INTO risk_assessments (document_id, risk_score, financial_risk, legal_risk, operational_risk, risk_reasons)
VALUES
    ('doc_54a7dc8c15940f54fc2a64d1de84daa3', 91, 'High', 'High', 'High', $j$[
        {
                "rule_id": "RISK_AUTO_RENEWAL",
                "title": "Automatic renewal without notice reminder",
                "severity": "high",
                "category": "legal",
                "evidence": {
                        "snippet": "This Agreement shall automatically renew for successive thirty-six (36) month terms unless either party delivers written notice of non-renewal.",
                        "page": 4
                }
        },
        {
                "rule_id": "RISK_LIABILITY_CAP_LOW",
                "title": "Liability cap below contract value",
                "severity": "high",
                "category": "financial",
                "evidence": {
                        "snippet": "In no event shall either party's aggregate liability exceed the total fees paid in the trailing twelve (12) months.",
                        "page": 9
                }
        },
        {
                "rule_id": "RISK_SHORT_NOTICE",
                "title": "Short termination notice period",
                "severity": "medium",
                "category": "operational",
                "evidence": {
                        "snippet": "Either party may terminate for cause upon fifteen (15) days written notice.",
                        "page": 4
                }
        },
        {
                "rule_id": "RISK_UNCAPPED_INDEMNITY",
                "title": "Indemnity scope not capped",
                "severity": "medium",
                "category": "legal",
                "evidence": {
                        "snippet": "Supplier shall indemnify and hold harmless the Customer against any and all claims arising from performance of this Agreement.",
                        "page": 8
                }
        },
        {
                "rule_id": "RISK_PAYMENT_TERMS_LONG",
                "title": "Payment terms exceed policy",
                "severity": "medium",
                "category": "financial",
                "evidence": {
                        "snippet": "Payment shall be due within sixty (60) days of invoice date.",
                        "page": 6
                }
        },
        {
                "rule_id": "RISK_FOREIGN_JURISDICTION",
                "title": "Governing law outside standard jurisdiction",
                "severity": "low",
                "category": "legal",
                "evidence": {
                        "snippet": "This Agreement shall be governed by the laws of the State of New York.",
                        "page": 11
                }
        },
        {
                "rule_id": "RISK_NO_SLA_CREDITS",
                "title": "No service level credits defined",
                "severity": "low",
                "category": "operational",
                "evidence": {
                        "snippet": "Supplier will use commercially reasonable efforts to maintain availability.",
                        "page": 7
                }
        }
]$j$::jsonb),
    ('doc_81671ec6b5356c0d5fce35a01ee82e8c', 84, 'High', 'High', 'Medium', $j$[
        {
                "rule_id": "RISK_AUTO_RENEWAL",
                "title": "Automatic renewal without notice reminder",
                "severity": "high",
                "category": "legal",
                "evidence": {
                        "snippet": "This Agreement shall automatically renew for successive thirty-six (36) month terms unless either party delivers written notice of non-renewal.",
                        "page": 4
                }
        },
        {
                "rule_id": "RISK_LIABILITY_CAP_LOW",
                "title": "Liability cap below contract value",
                "severity": "high",
                "category": "financial",
                "evidence": {
                        "snippet": "In no event shall either party's aggregate liability exceed the total fees paid in the trailing twelve (12) months.",
                        "page": 9
                }
        },
        {
                "rule_id": "RISK_SHORT_NOTICE",
                "title": "Short termination notice period",
                "severity": "medium",
                "category": "operational",
                "evidence": {
                        "snippet": "Either party may terminate for cause upon fifteen (15) days written notice.",
                        "page": 4
                }
        },
        {
                "rule_id": "RISK_UNCAPPED_INDEMNITY",
                "title": "Indemnity scope not capped",
                "severity": "medium",
                "category": "legal",
                "evidence": {
                        "snippet": "Supplier shall indemnify and hold harmless the Customer against any and all claims arising from performance of this Agreement.",
                        "page": 8
                }
        },
        {
                "rule_id": "RISK_PAYMENT_TERMS_LONG",
                "title": "Payment terms exceed policy",
                "severity": "medium",
                "category": "financial",
                "evidence": {
                        "snippet": "Payment shall be due within sixty (60) days of invoice date.",
                        "page": 6
                }
        },
        {
                "rule_id": "RISK_FOREIGN_JURISDICTION",
                "title": "Governing law outside standard jurisdiction",
                "severity": "low",
                "category": "legal",
                "evidence": {
                        "snippet": "This Agreement shall be governed by the laws of the State of New York.",
                        "page": 11
                }
        },
        {
                "rule_id": "RISK_NO_SLA_CREDITS",
                "title": "No service level credits defined",
                "severity": "low",
                "category": "operational",
                "evidence": {
                        "snippet": "Supplier will use commercially reasonable efforts to maintain availability.",
                        "page": 7
                }
        }
]$j$::jsonb),
    ('doc_a0a9abdbb05e2184e56ebe4602caa818', 78, 'High', 'High', 'Low', $j$[
        {
                "rule_id": "RISK_AUTO_RENEWAL",
                "title": "Automatic renewal without notice reminder",
                "severity": "high",
                "category": "legal",
                "evidence": {
                        "snippet": "This Agreement shall automatically renew for successive thirty-six (36) month terms unless either party delivers written notice of non-renewal.",
                        "page": 4
                }
        },
        {
                "rule_id": "RISK_LIABILITY_CAP_LOW",
                "title": "Liability cap below contract value",
                "severity": "high",
                "category": "financial",
                "evidence": {
                        "snippet": "In no event shall either party's aggregate liability exceed the total fees paid in the trailing twelve (12) months.",
                        "page": 9
                }
        },
        {
                "rule_id": "RISK_SHORT_NOTICE",
                "title": "Short termination notice period",
                "severity": "medium",
                "category": "operational",
                "evidence": {
                        "snippet": "Either party may terminate for cause upon fifteen (15) days written notice.",
                        "page": 4
                }
        },
        {
                "rule_id": "RISK_UNCAPPED_INDEMNITY",
                "title": "Indemnity scope not capped",
                "severity": "medium",
                "category": "legal",
                "evidence": {
                        "snippet": "Supplier shall indemnify and hold harmless the Customer against any and all claims arising from performance of this Agreement.",
                        "page": 8
                }
        },
        {
                "rule_id": "RISK_PAYMENT_TERMS_LONG",
                "title": "Payment terms exceed policy",
                "severity": "medium",
                "category": "financial",
                "evidence": {
                        "snippet": "Payment shall be due within sixty (60) days of invoice date.",
                        "page": 6
                }
        },
        {
                "rule_id": "RISK_FOREIGN_JURISDICTION",
                "title": "Governing law outside standard jurisdiction",
                "severity": "low",
                "category": "legal",
                "evidence": {
                        "snippet": "This Agreement shall be governed by the laws of the State of New York.",
                        "page": 11
                }
        },
        {
                "rule_id": "RISK_NO_SLA_CREDITS",
                "title": "No service level credits defined",
                "severity": "low",
                "category": "operational",
                "evidence": {
                        "snippet": "Supplier will use commercially reasonable efforts to maintain availability.",
                        "page": 7
                }
        }
]$j$::jsonb),
    ('doc_ac3d7a1f747a0dc72525655a3bd710b9', 71, 'Medium', 'High', 'High', $j$[
        {
                "rule_id": "RISK_AUTO_RENEWAL",
                "title": "Automatic renewal without notice reminder",
                "severity": "high",
                "category": "legal",
                "evidence": {
                        "snippet": "This Agreement shall automatically renew for successive thirty-six (36) month terms unless either party delivers written notice of non-renewal.",
                        "page": 4
                }
        },
        {
                "rule_id": "RISK_LIABILITY_CAP_LOW",
                "title": "Liability cap below contract value",
                "severity": "high",
                "category": "financial",
                "evidence": {
                        "snippet": "In no event shall either party's aggregate liability exceed the total fees paid in the trailing twelve (12) months.",
                        "page": 9
                }
        },
        {
                "rule_id": "RISK_SHORT_NOTICE",
                "title": "Short termination notice period",
                "severity": "medium",
                "category": "operational",
                "evidence": {
                        "snippet": "Either party may terminate for cause upon fifteen (15) days written notice.",
                        "page": 4
                }
        },
        {
                "rule_id": "RISK_UNCAPPED_INDEMNITY",
                "title": "Indemnity scope not capped",
                "severity": "medium",
                "category": "legal",
                "evidence": {
                        "snippet": "Supplier shall indemnify and hold harmless the Customer against any and all claims arising from performance of this Agreement.",
                        "page": 8
                }
        },
        {
                "rule_id": "RISK_PAYMENT_TERMS_LONG",
                "title": "Payment terms exceed policy",
                "severity": "medium",
                "category": "financial",
                "evidence": {
                        "snippet": "Payment shall be due within sixty (60) days of invoice date.",
                        "page": 6
                }
        },
        {
                "rule_id": "RISK_FOREIGN_JURISDICTION",
                "title": "Governing law outside standard jurisdiction",
                "severity": "low",
                "category": "legal",
                "evidence": {
                        "snippet": "This Agreement shall be governed by the laws of the State of New York.",
                        "page": 11
                }
        },
        {
                "rule_id": "RISK_NO_SLA_CREDITS",
                "title": "No service level credits defined",
                "severity": "low",
                "category": "operational",
                "evidence": {
                        "snippet": "Supplier will use commercially reasonable efforts to maintain availability.",
                        "page": 7
                }
        }
]$j$::jsonb),
    ('doc_b56316a70164e265b93850d9641a02a6', 67, 'Medium', 'High', 'Medium', $j$[
        {
                "rule_id": "RISK_AUTO_RENEWAL",
                "title": "Automatic renewal without notice reminder",
                "severity": "high",
                "category": "legal",
                "evidence": {
                        "snippet": "This Agreement shall automatically renew for successive thirty-six (36) month terms unless either party delivers written notice of non-renewal.",
                        "page": 4
                }
        },
        {
                "rule_id": "RISK_LIABILITY_CAP_LOW",
                "title": "Liability cap below contract value",
                "severity": "high",
                "category": "financial",
                "evidence": {
                        "snippet": "In no event shall either party's aggregate liability exceed the total fees paid in the trailing twelve (12) months.",
                        "page": 9
                }
        },
        {
                "rule_id": "RISK_SHORT_NOTICE",
                "title": "Short termination notice period",
                "severity": "medium",
                "category": "operational",
                "evidence": {
                        "snippet": "Either party may terminate for cause upon fifteen (15) days written notice.",
                        "page": 4
                }
        },
        {
                "rule_id": "RISK_UNCAPPED_INDEMNITY",
                "title": "Indemnity scope not capped",
                "severity": "medium",
                "category": "legal",
                "evidence": {
                        "snippet": "Supplier shall indemnify and hold harmless the Customer against any and all claims arising from performance of this Agreement.",
                        "page": 8
                }
        },
        {
                "rule_id": "RISK_PAYMENT_TERMS_LONG",
                "title": "Payment terms exceed policy",
                "severity": "medium",
                "category": "financial",
                "evidence": {
                        "snippet": "Payment shall be due within sixty (60) days of invoice date.",
                        "page": 6
                }
        },
        {
                "rule_id": "RISK_FOREIGN_JURISDICTION",
                "title": "Governing law outside standard jurisdiction",
                "severity": "low",
                "category": "legal",
                "evidence": {
                        "snippet": "This Agreement shall be governed by the laws of the State of New York.",
                        "page": 11
                }
        },
        {
                "rule_id": "RISK_NO_SLA_CREDITS",
                "title": "No service level credits defined",
                "severity": "low",
                "category": "operational",
                "evidence": {
                        "snippet": "Supplier will use commercially reasonable efforts to maintain availability.",
                        "page": 7
                }
        }
]$j$::jsonb),
    ('doc_9b06d5606f0b831865ac3fb2eaf0e889', 63, 'Low', 'High', 'Medium', $j$[
        {
                "rule_id": "RISK_AUTO_RENEWAL",
                "title": "Automatic renewal without notice reminder",
                "severity": "high",
                "category": "legal",
                "evidence": {
                        "snippet": "This Agreement shall automatically renew for successive thirty-six (36) month terms unless either party delivers written notice of non-renewal.",
                        "page": 4
                }
        },
        {
                "rule_id": "RISK_LIABILITY_CAP_LOW",
                "title": "Liability cap below contract value",
                "severity": "high",
                "category": "financial",
                "evidence": {
                        "snippet": "In no event shall either party's aggregate liability exceed the total fees paid in the trailing twelve (12) months.",
                        "page": 9
                }
        },
        {
                "rule_id": "RISK_SHORT_NOTICE",
                "title": "Short termination notice period",
                "severity": "medium",
                "category": "operational",
                "evidence": {
                        "snippet": "Either party may terminate for cause upon fifteen (15) days written notice.",
                        "page": 4
                }
        },
        {
                "rule_id": "RISK_UNCAPPED_INDEMNITY",
                "title": "Indemnity scope not capped",
                "severity": "medium",
                "category": "legal",
                "evidence": {
                        "snippet": "Supplier shall indemnify and hold harmless the Customer against any and all claims arising from performance of this Agreement.",
                        "page": 8
                }
        },
        {
                "rule_id": "RISK_PAYMENT_TERMS_LONG",
                "title": "Payment terms exceed policy",
                "severity": "medium",
                "category": "financial",
                "evidence": {
                        "snippet": "Payment shall be due within sixty (60) days of invoice date.",
                        "page": 6
                }
        },
        {
                "rule_id": "RISK_FOREIGN_JURISDICTION",
                "title": "Governing law outside standard jurisdiction",
                "severity": "low",
                "category": "legal",
                "evidence": {
                        "snippet": "This Agreement shall be governed by the laws of the State of New York.",
                        "page": 11
                }
        },
        {
                "rule_id": "RISK_NO_SLA_CREDITS",
                "title": "No service level credits defined",
                "severity": "low",
                "category": "operational",
                "evidence": {
                        "snippet": "Supplier will use commercially reasonable efforts to maintain availability.",
                        "page": 7
                }
        }
]$j$::jsonb),
    ('doc_d66d11ac0359344a357b9a88ad388b4e', 58, 'High', 'Low', 'Medium', $j$[
        {
                "rule_id": "RISK_SHORT_NOTICE",
                "title": "Short termination notice period",
                "severity": "medium",
                "category": "operational",
                "evidence": {
                        "snippet": "Either party may terminate for cause upon fifteen (15) days written notice.",
                        "page": 4
                }
        },
        {
                "rule_id": "RISK_UNCAPPED_INDEMNITY",
                "title": "Indemnity scope not capped",
                "severity": "medium",
                "category": "legal",
                "evidence": {
                        "snippet": "Supplier shall indemnify and hold harmless the Customer against any and all claims arising from performance of this Agreement.",
                        "page": 8
                }
        },
        {
                "rule_id": "RISK_PAYMENT_TERMS_LONG",
                "title": "Payment terms exceed policy",
                "severity": "medium",
                "category": "financial",
                "evidence": {
                        "snippet": "Payment shall be due within sixty (60) days of invoice date.",
                        "page": 6
                }
        },
        {
                "rule_id": "RISK_FOREIGN_JURISDICTION",
                "title": "Governing law outside standard jurisdiction",
                "severity": "low",
                "category": "legal",
                "evidence": {
                        "snippet": "This Agreement shall be governed by the laws of the State of New York.",
                        "page": 11
                }
        },
        {
                "rule_id": "RISK_NO_SLA_CREDITS",
                "title": "No service level credits defined",
                "severity": "low",
                "category": "operational",
                "evidence": {
                        "snippet": "Supplier will use commercially reasonable efforts to maintain availability.",
                        "page": 7
                }
        }
]$j$::jsonb),
    ('doc_05219d93574e8e2e1303fe085ff2ac7c', 49, 'Medium', 'Medium', 'Low', $j$[
        {
                "rule_id": "RISK_SHORT_NOTICE",
                "title": "Short termination notice period",
                "severity": "medium",
                "category": "operational",
                "evidence": {
                        "snippet": "Either party may terminate for cause upon fifteen (15) days written notice.",
                        "page": 4
                }
        },
        {
                "rule_id": "RISK_UNCAPPED_INDEMNITY",
                "title": "Indemnity scope not capped",
                "severity": "medium",
                "category": "legal",
                "evidence": {
                        "snippet": "Supplier shall indemnify and hold harmless the Customer against any and all claims arising from performance of this Agreement.",
                        "page": 8
                }
        },
        {
                "rule_id": "RISK_PAYMENT_TERMS_LONG",
                "title": "Payment terms exceed policy",
                "severity": "medium",
                "category": "financial",
                "evidence": {
                        "snippet": "Payment shall be due within sixty (60) days of invoice date.",
                        "page": 6
                }
        },
        {
                "rule_id": "RISK_FOREIGN_JURISDICTION",
                "title": "Governing law outside standard jurisdiction",
                "severity": "low",
                "category": "legal",
                "evidence": {
                        "snippet": "This Agreement shall be governed by the laws of the State of New York.",
                        "page": 11
                }
        },
        {
                "rule_id": "RISK_NO_SLA_CREDITS",
                "title": "No service level credits defined",
                "severity": "low",
                "category": "operational",
                "evidence": {
                        "snippet": "Supplier will use commercially reasonable efforts to maintain availability.",
                        "page": 7
                }
        }
]$j$::jsonb),
    ('doc_17e252c2b07594ab8e0c7fd0ab810acd', 45, 'Medium', 'Low', 'Medium', $j$[
        {
                "rule_id": "RISK_SHORT_NOTICE",
                "title": "Short termination notice period",
                "severity": "medium",
                "category": "operational",
                "evidence": {
                        "snippet": "Either party may terminate for cause upon fifteen (15) days written notice.",
                        "page": 4
                }
        },
        {
                "rule_id": "RISK_UNCAPPED_INDEMNITY",
                "title": "Indemnity scope not capped",
                "severity": "medium",
                "category": "legal",
                "evidence": {
                        "snippet": "Supplier shall indemnify and hold harmless the Customer against any and all claims arising from performance of this Agreement.",
                        "page": 8
                }
        },
        {
                "rule_id": "RISK_PAYMENT_TERMS_LONG",
                "title": "Payment terms exceed policy",
                "severity": "medium",
                "category": "financial",
                "evidence": {
                        "snippet": "Payment shall be due within sixty (60) days of invoice date.",
                        "page": 6
                }
        },
        {
                "rule_id": "RISK_FOREIGN_JURISDICTION",
                "title": "Governing law outside standard jurisdiction",
                "severity": "low",
                "category": "legal",
                "evidence": {
                        "snippet": "This Agreement shall be governed by the laws of the State of New York.",
                        "page": 11
                }
        },
        {
                "rule_id": "RISK_NO_SLA_CREDITS",
                "title": "No service level credits defined",
                "severity": "low",
                "category": "operational",
                "evidence": {
                        "snippet": "Supplier will use commercially reasonable efforts to maintain availability.",
                        "page": 7
                }
        }
]$j$::jsonb),
    ('doc_322c5345b1f1a85b199268991e8817f6', 41, 'Medium', 'Medium', 'Low', $j$[
        {
                "rule_id": "RISK_PAYMENT_TERMS_LONG",
                "title": "Payment terms exceed policy",
                "severity": "medium",
                "category": "financial",
                "evidence": {
                        "snippet": "Payment shall be due within sixty (60) days of invoice date.",
                        "page": 6
                }
        },
        {
                "rule_id": "RISK_FOREIGN_JURISDICTION",
                "title": "Governing law outside standard jurisdiction",
                "severity": "low",
                "category": "legal",
                "evidence": {
                        "snippet": "This Agreement shall be governed by the laws of the State of New York.",
                        "page": 11
                }
        },
        {
                "rule_id": "RISK_NO_SLA_CREDITS",
                "title": "No service level credits defined",
                "severity": "low",
                "category": "operational",
                "evidence": {
                        "snippet": "Supplier will use commercially reasonable efforts to maintain availability.",
                        "page": 7
                }
        }
]$j$::jsonb),
    ('doc_7d8a7777a894c67e2c4f82322f0d38cd', 38, 'Medium', 'Low', 'Low', $j$[
        {
                "rule_id": "RISK_PAYMENT_TERMS_LONG",
                "title": "Payment terms exceed policy",
                "severity": "medium",
                "category": "financial",
                "evidence": {
                        "snippet": "Payment shall be due within sixty (60) days of invoice date.",
                        "page": 6
                }
        },
        {
                "rule_id": "RISK_FOREIGN_JURISDICTION",
                "title": "Governing law outside standard jurisdiction",
                "severity": "low",
                "category": "legal",
                "evidence": {
                        "snippet": "This Agreement shall be governed by the laws of the State of New York.",
                        "page": 11
                }
        },
        {
                "rule_id": "RISK_NO_SLA_CREDITS",
                "title": "No service level credits defined",
                "severity": "low",
                "category": "operational",
                "evidence": {
                        "snippet": "Supplier will use commercially reasonable efforts to maintain availability.",
                        "page": 7
                }
        }
]$j$::jsonb),
    ('doc_289cfb3aa14ac20f24e83b492a1f984f', 34, 'Low', 'Medium', 'Medium', $j$[
        {
                "rule_id": "RISK_PAYMENT_TERMS_LONG",
                "title": "Payment terms exceed policy",
                "severity": "medium",
                "category": "financial",
                "evidence": {
                        "snippet": "Payment shall be due within sixty (60) days of invoice date.",
                        "page": 6
                }
        },
        {
                "rule_id": "RISK_FOREIGN_JURISDICTION",
                "title": "Governing law outside standard jurisdiction",
                "severity": "low",
                "category": "legal",
                "evidence": {
                        "snippet": "This Agreement shall be governed by the laws of the State of New York.",
                        "page": 11
                }
        },
        {
                "rule_id": "RISK_NO_SLA_CREDITS",
                "title": "No service level credits defined",
                "severity": "low",
                "category": "operational",
                "evidence": {
                        "snippet": "Supplier will use commercially reasonable efforts to maintain availability.",
                        "page": 7
                }
        }
]$j$::jsonb),
    ('doc_f392713ab1d3ce8472d4ae6916dbb6bd', 31, 'Low', 'Low', 'Medium', $j$[
        {
                "rule_id": "RISK_PAYMENT_TERMS_LONG",
                "title": "Payment terms exceed policy",
                "severity": "medium",
                "category": "financial",
                "evidence": {
                        "snippet": "Payment shall be due within sixty (60) days of invoice date.",
                        "page": 6
                }
        },
        {
                "rule_id": "RISK_FOREIGN_JURISDICTION",
                "title": "Governing law outside standard jurisdiction",
                "severity": "low",
                "category": "legal",
                "evidence": {
                        "snippet": "This Agreement shall be governed by the laws of the State of New York.",
                        "page": 11
                }
        },
        {
                "rule_id": "RISK_NO_SLA_CREDITS",
                "title": "No service level credits defined",
                "severity": "low",
                "category": "operational",
                "evidence": {
                        "snippet": "Supplier will use commercially reasonable efforts to maintain availability.",
                        "page": 7
                }
        }
]$j$::jsonb),
    ('doc_9f52e08babc93b64c58e3b8dad8db9fe', 29, 'Low', 'Medium', 'Low', $j$[
        {
                "rule_id": "RISK_FOREIGN_JURISDICTION",
                "title": "Governing law outside standard jurisdiction",
                "severity": "low",
                "category": "legal",
                "evidence": {
                        "snippet": "This Agreement shall be governed by the laws of the State of New York.",
                        "page": 11
                }
        },
        {
                "rule_id": "RISK_NO_SLA_CREDITS",
                "title": "No service level credits defined",
                "severity": "low",
                "category": "operational",
                "evidence": {
                        "snippet": "Supplier will use commercially reasonable efforts to maintain availability.",
                        "page": 7
                }
        }
]$j$::jsonb),
    ('doc_793eae13b4e7fe07d5aeb3ad3b072f33', 26, 'Low', 'Low', 'Medium', $j$[
        {
                "rule_id": "RISK_FOREIGN_JURISDICTION",
                "title": "Governing law outside standard jurisdiction",
                "severity": "low",
                "category": "legal",
                "evidence": {
                        "snippet": "This Agreement shall be governed by the laws of the State of New York.",
                        "page": 11
                }
        },
        {
                "rule_id": "RISK_NO_SLA_CREDITS",
                "title": "No service level credits defined",
                "severity": "low",
                "category": "operational",
                "evidence": {
                        "snippet": "Supplier will use commercially reasonable efforts to maintain availability.",
                        "page": 7
                }
        }
]$j$::jsonb),
    ('doc_1fbeb044f4939a6dcd83ba9735995f0e', 23, 'Low', 'Low', 'Low', $j$[
        {
                "rule_id": "RISK_FOREIGN_JURISDICTION",
                "title": "Governing law outside standard jurisdiction",
                "severity": "low",
                "category": "legal",
                "evidence": {
                        "snippet": "This Agreement shall be governed by the laws of the State of New York.",
                        "page": 11
                }
        },
        {
                "rule_id": "RISK_NO_SLA_CREDITS",
                "title": "No service level credits defined",
                "severity": "low",
                "category": "operational",
                "evidence": {
                        "snippet": "Supplier will use commercially reasonable efforts to maintain availability.",
                        "page": 7
                }
        }
]$j$::jsonb),
    ('doc_5e63340ef6e93f86d234471bb8ecb9db', 19, 'Low', 'Low', 'Low', $j$[
        {
                "rule_id": "RISK_NO_SLA_CREDITS",
                "title": "No service level credits defined",
                "severity": "low",
                "category": "operational",
                "evidence": {
                        "snippet": "Supplier will use commercially reasonable efforts to maintain availability.",
                        "page": 7
                }
        }
]$j$::jsonb),
    ('doc_7715cccb66d226f435b644714c8984e9', 15, 'Low', 'Low', 'Low', $j$[
        {
                "rule_id": "RISK_NO_SLA_CREDITS",
                "title": "No service level credits defined",
                "severity": "low",
                "category": "operational",
                "evidence": {
                        "snippet": "Supplier will use commercially reasonable efforts to maintain availability.",
                        "page": 7
                }
        }
]$j$::jsonb),
    ('doc_5741a34ea0146a3ee5a5f98f53beb9f1', 9, 'Low', 'Low', 'Low', $j$[
        {
                "rule_id": "RISK_NO_SLA_CREDITS",
                "title": "No service level credits defined",
                "severity": "low",
                "category": "operational",
                "evidence": {
                        "snippet": "Supplier will use commercially reasonable efforts to maintain availability.",
                        "page": 7
                }
        }
]$j$::jsonb),
    ('doc_8f5f64c5ab9e793985e569ff8dd574b0', 7, 'Low', 'Low', 'Low', $j$[
        {
                "rule_id": "RISK_NO_SLA_CREDITS",
                "title": "No service level credits defined",
                "severity": "low",
                "category": "operational",
                "evidence": {
                        "snippet": "Supplier will use commercially reasonable efforts to maintain availability.",
                        "page": 7
                }
        }
]$j$::jsonb)
ON CONFLICT (document_id) DO UPDATE SET
    risk_score = EXCLUDED.risk_score,
    financial_risk = EXCLUDED.financial_risk,
    legal_risk = EXCLUDED.legal_risk,
    operational_risk = EXCLUDED.operational_risk,
    risk_reasons = EXCLUDED.risk_reasons;

COMMIT;
