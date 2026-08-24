# Contributing — DocuMind AI

## Ground rules

1. **Never commit secrets**: `terraform.tfvars`, `backend.hcl`, `*.pem`, `.env`, kubeconfigs, tokens. Only `*.example` files. CI and review enforce this.
2. **Never push to `main` directly** — everything goes through a PR.
3. Every service exposes `/liveness` and `/readiness`, reads config from environment variables, and emits structured JSON logs with `request_id` + `trace_id`.

## Branching

```text
main              # protected, always deployable
feat/<role>-<what>   # feat/ai-adapter-interface, feat/cloud-networking-module
fix/<what>
docs/<what>
```

One PR = one reviewable unit. Keep PRs small (< ~400 lines diff where possible).

## Commit style

Conventional, short subject + body when needed:

```text
feat(processing): add classification worker with retry
docs(adr): draft ADR-005 vector store options
fix(ci): skip trivy job when no Dockerfile changed
```

## PR checklist (reviewer will reject without)

- [ ] Tests pass locally (`docker compose up -d postgres redis` first if needed)
- [ ] No secrets / real OCIDs / credentials in diff
- [ ] Probes + resource requests/limits included for any new Deployment
- [ ] Structured logging with `request_id`/`trace_id` for any new code path
- [ ] Docs updated (README of the folder, ADR if an architectural decision was made)
- [ ] If Terraform changed: `terraform fmt` + `terraform validate` clean, plan output attached

## Local development

```powershell
docker compose up -d postgres redis   # data tier (pgvector + Redis)
# then run your service locally against localhost:5432 / localhost:6379
```

## Ownership

See [docs/team/ROLES.md](docs/team/ROLES.md) for who owns which folder.
PRs touching a folder should request review from that folder's owner.
