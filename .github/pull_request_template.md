<!-- What does this PR do? Link the issue/task if any. -->

## Role / folder touched

- Role: <!-- e.g. Backend Lead (role 3) -->
- Folder: <!-- e.g. services/document-service -->

## Checklist

- [ ] No secrets, real OCIDs, tokens, or credentials in this diff
- [ ] Tests pass locally (`docker compose up -d postgres redis` if needed)
- [ ] New Deployments include probes + resource requests/limits + securityContext
- [ ] Structured logging with `request_id` / `trace_id` for new code paths
- [ ] Docs updated (folder README, ADR if a decision was made)
- [ ] If Terraform changed: `terraform fmt` + `validate` clean, plan summary attached
- [ ] Folder owner review requested

## Evidence (screenshots / test output / plan output)

<!-- paste or link -->
