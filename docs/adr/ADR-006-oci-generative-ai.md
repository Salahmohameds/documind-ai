# ADR-006 — AI Provider: OCI Generative AI behind an Adapter

**Status:** Accepted (pending region-access confirmation)
**Date:** 2026-08-24
**Deciders:** DocuMind team

## Problem

Which LLM/embedding provider powers classification support, extraction
assists, risk analysis, and RAG answers — and how do workloads authenticate?

## Options

1. Direct OpenAI/Azure OpenAI API keys stored as K8s secrets.
2. **OCI Generative AI via IAM dynamic-group auth**, behind an internal
   adapter interface with an OpenAI-compatible fallback.
3. Self-hosted open models on OKE.

## Decision

Option 2. All calls flow through an internal `AI Adapter`:

```text
services → AI Adapter → OCI Generative AI (chat + embeddings [+ rerank])
                     ↘ fallback: OpenAI-compatible endpoint (config-only swap)
```

Workload auth: OKE workload identity → Dynamic Group → least-privilege policy
scoped to the intern compartment.

## Why

* No external API credentials leave the tenancy — inference stays inside OCI;
  access governed by IAM, not pasted secrets.
* Adapter isolates provider specifics → model/provider swaps are config
  changes; tests mock the interface.
* Option 3 is out: no GPU budget/time; listed as future work.

## Contingency

**Updated 2026-08-26 (role 4).** The original text jumped straight from
"unavailable in `me-jeddah-1`" to the OpenAI-compatible fallback. That skips a
step, and skipping it would throw away the IAM story for nothing.

`me-jeddah-1` does **not** host OCI Generative AI. This is knowable today and
the answer is no — the region does not appear in Oracle's availability tables
at all. The service runs in `sa-saopaulo-1`, `eu-frankfurt-1`, `ap-hyderabad-1`,
`ap-osaka-1`, **`me-riyadh-1`**, **`me-abudhabi-1`**, **`me-dubai-1`**,
`uk-london-1`, `us-ashburn-1`, `us-chicago-1`, `us-phoenix-1`.

**That is not fatal, because compartments in OCI are global.** The Generative AI
API takes a `compartmentId`, and the SDK client is *separately* pointed at a
region endpoint. The two are independent. If the tenancy is subscribed to any
Generative AI region — `me-riyadh-1` is adjacent and the most likely
subscription for a Saudi-hosted tenancy — DocuMind can call Generative AI there
using a Jeddah compartment OCID. Dynamic group unchanged, policy unchanged, no
data leaves OCI, and this ADR stands as written.

`services/ai-service` implements exactly this: `OCI_REGION` and
`OCI_COMPARTMENT_ID` are independent settings and neither is derived from the
other.

### Fallback order

1. **Tenancy subscribed to a Generative AI region** → use it, targeting that
   region's endpoint with the project compartment OCID. No architectural
   compromise.
2. **Not subscribed** → ask the mentor to subscribe. It is a tenancy-admin
   action and he offered to grant permissions where possible. One-line ask.
3. **Neither** → *then* the OpenAI-compatible fallback
   (`AI_BACKEND=openai_compat`), which also covers Google Gemini via its
   OpenAI-compatible endpoint. Trade-offs below.

### The check that actually decides this (role 1 — needs OCI access)

```bash
oci iam region-subscription list
```

Then, for each subscribed region on the list above:

```bash
oci generative-ai model list \
  --compartment-id <COMPARTMENT_OCID> \
  --region me-riyadh-1 \
  --all
```

`docs/assessment/pre-flight-findings.md` currently asks *"are models listed in
`me-jeddah-1`?"* — a question whose answer is a guaranteed **no**, which would
falsely trigger step 3. That template belongs to role 1 and should be corrected
to ask the region-subscription question instead.

### If it does come to the OpenAI-compatible fallback

Recorded honestly, because this is the weakest link in the architecture and it
sits under the AI Engineer's name:

* **It breaks the security narrative.** An API key in a Kubernetes Secret is
  precisely what option 2 exists to avoid.
* **Document text leaves the tenancy** over the public internet to a third
  party. For a product whose headline feature is detecting PII in contracts,
  that is a contradiction a reviewer will enjoy finding. `app/redaction.py`
  reduces the blast radius; it does not remove it.
* **Free-tier terms.** Free tiers have historically trained on submitted
  content. Verify current terms; if used, **synthetic documents only**.
* **Rate limits** will not survive a k6 run.
* **Egress.** Worker pods sit in a private subnet, so calls route through the
  NAT gateway — a new rule and a visible hole in "everything stays private".

Until this decision closes, `AI_BACKEND=mock` is the default and the entire
service — every endpoint, the full test suite — runs offline with no credential.
See ADR-008 for the related embeddings boundary decision.

## Trade-offs

* Model catalog/limits differ from consumer APIs; prompt tuning required.
* Extra abstraction layer to maintain (small, single module).
