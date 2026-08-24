# Week-0 Pre-Flight Findings

> Owner: Cloud Lead (role 1). Fill this in during W0 — decisions D1–D5 in the
> proposal (§26) close based on these results. Run against compartment
> `intern-18-salah-abdelhady-cmp`, region `me-jeddah-1`.

## 1. OCI Generative AI access (decision D1)

```powershell
oci generative-ai model list --compartment-id <COMPARTMENT_OCID> --all
```

| Check | Result | Notes |
|-------|--------|-------|
| Models listed in me-jeddah-1 | ☐ yes / ☐ no | |
| Chat model available (which?) | ☐ | |
| Embedding model available (which?) | ☐ | |
| Rerank available | ☐ | |
| Tenancy enabled for GenAI | ☐ | |
| Dynamic group + policy works from a test workload | ☐ | |

**D1 outcome:** OCI GenAI ☐ confirmed / ☐ fallback to OpenAI-compatible endpoint (ADR-006 contingency)

## 2. Quotas & availability (decision D3 inputs)

```powershell
oci limits service list --compartment-id <COMPARTMENT_OCID>
oci limits limit-definition list --service-name compute --compartment-id <COMPARTMENT_OCID> --all
oci limits limit-definition list --service-name oke --compartment-id <COMPARTMENT_OCID> --all
oci limits limit-definition list --service-name load-balancer --compartment-id <COMPARTMENT_OCID> --all
oci limits resource-availability get --service-name compute --limit-name standard-e4-core-count --availability-domain "<AD>" --compartment-id <COMPARTMENT_OCID>
oci os ns get
```

| Resource | Limit | Available | Enough for plan? |
|----------|-------|-----------|------------------|
| OKE clusters | | | |
| E4.Flex OCPUs | | | |
| Load balancers | | | |
| Block volumes | | | |
| Object Storage | | | |

## 3. IAM capability

| Check | Result |
|-------|--------|
| Can create dynamic groups in compartment | ☐ |
| Can create policies | ☐ |
| Mentor-approved provisioning scope confirmed | ☐ |

## 4. Decisions closed in W0

| Decision | Outcome |
|----------|---------|
| D1 AI provider | |
| D2 queue (lean: Redis Streams) | |
| D3 vector store (lean: pgvector / 23ai if capacity) | |
| D4 frontend (lean: Streamlit) | |
| D5 monolith baseline host (lean: OCI Compute VM) | |

Recorded by: ____________  Date: ____________
