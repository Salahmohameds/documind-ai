#!/usr/bin/env bash
# OCI pre-flight checks for the DocuMind demo burst.
# Verifies tooling, authentication, target compartment, availability domains,
# service availability, shape/quota signals and OKE readiness BEFORE any
# terraform apply. Unknown/unverifiable items are WARN, hard blockers FAIL.
#
# Usage:
#   ./scripts/oci-preflight.sh [--compartment <ocid>] [--region <key>]
# Falls back to OCI_COMPARTMENT_OCID / OCI_REGION env vars, then to
# terraform/environments/demo/terraform.tfvars when present.

set -euo pipefail

COMPARTMENT="${OCI_COMPARTMENT_OCID:-}"
REGION="${OCI_REGION:-}"
TENANCY="${OCI_TENANCY_OCID:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --compartment) COMPARTMENT="$2"; shift 2 ;;
    --region)      REGION="$2"; shift 2 ;;
    *) echo "unknown arg: $1"; exit 2 ;;
  esac
done

PASS=0; WARN=0; FAIL=0
ok()   { printf " [PASS] %s\n" "$1"; PASS=$((PASS+1)); }
warn() { printf " [WARN] %s\n" "$1"; WARN=$((WARN+1)); }
bad()  { printf " [FAIL] %s\n" "$1"; FAIL=$((FAIL+1)); }
info() { printf " [INFO] %s\n" "$1"; }

command -v oci >/dev/null 2>&1 && ok "OCI CLI installed ($(oci --version))" || bad "OCI CLI not installed"

TF_BIN="${TERRAFORM_BIN:-terraform}"
if command -v "$TF_BIN" >/dev/null 2>&1; then
  TFV="$($TF_BIN version -json | sed -n 's/.*"terraform_version":"\([^"]*\)".*/\1/p')"
  MAJOR=$(echo "$TFV" | cut -d. -f2)
  if [[ "${MAJOR:-0}" -ge 12 ]]; then
    ok "Terraform $TFV (native oci backend needs >= 1.12)"
  else
    bad "Terraform $TFV too old — environments need >= 1.12 for the native oci backend"
  fi
else
  bad "Terraform not found"
fi

for extra in kubectl tflint; do
  command -v "$extra" >/dev/null 2>&1 && ok "$extra present" || warn "$extra missing (needed later, not a blocker)"
done

# ---------------------------------------------------------------- auth ----
if NS=$(oci os ns get --query 'data' -r 2>/dev/null); then
  ok "OCI authentication works (namespace resolved)"
else
  bad "Cannot authenticate to OCI (check ~/.oci/config or OCI_* env vars)"
fi

# ------------------------------------------------------- tfvars fallback --
if [[ -z "$COMPARTMENT" || -z "$REGION" ]]; then
  TV="terraform/environments/demo/terraform.tfvars"
  if [[ -f "$TV" ]]; then
    info "reading region/compartment from $TV"
    [[ -z "$REGION" ]]      && REGION=$(grep -E '^\s*region\s*=' "$TV" | head -1 | sed 's/.*=\s*"\(.*\)"/\1/')
    [[ -z "$COMPARTMENT" ]] && COMPARTMENT=$(grep -E '^\s*compartment_id\s*=' "$TV" | head -1 | sed 's/.*=\s*"\(.*\)"/\1/')
  fi
fi

# ------------------------------------------------------------- region -----
if [[ -n "$REGION" ]]; then
  if oci iam region-subscription list --query "data[?\"region-name\"=='$REGION']" 2>/dev/null | grep -q "$REGION"; then
    ok "Region subscribed: $REGION"
  else
    bad "Region $REGION is not part of this tenancy"
  fi
else
  warn "No region given; skipping region check"
fi

# -------------------------------------------------------- compartment -----
if [[ -n "$COMPARTMENT" ]]; then
  if CMP_STATE=$(oci iam compartment get --compartment-id "$COMPARTMENT" --query 'data."lifecycle-state"' -r 2>/dev/null); then
    [[ "$CMP_STATE" == "ACTIVE" ]] \
      && ok "Compartment ACTIVE and accessible" \
      || bad "Compartment lifecycle-state = $CMP_STATE"
  else
    bad "Compartment not readable with current credentials"
  fi
else
  bad "No compartment OCID provided (arg, env or tfvars)"
fi

# ---------------------------------------------------------------- ADs -----
if ADS=$(oci iam availability-domain list --all --query 'data[].name' -r 2>/dev/null | tr -d '[]",'); then
  N_ADS=$(wc -w <<< "$ADS")
  ok "Availability domains visible ($N_ADS): $(echo $ADS | awk '{print $1, $2}')"
else
  warn "Could not list availability domains"
fi

# ------------------------------------------- service availability (limits) -
if command -v jq >/dev/null 2>&1; then
  # NOTE: service catalog requires tenancy-scope read; some restricted users
  # get ServiceError here — that becomes a WARN, not a FAIL.
  SERVICES=$(oci limits service list --compartment-id "${TENANCY:-$COMPARTMENT}" \
               --all --query 'data[].name' -r 2>/dev/null | tr -d '[]",')
  for svc in oke lbaas database objectstorage; do
    if echo "$SERVICES" | grep -qi "$svc"; then
      ok "Service available in limits catalog: $svc"
    else
      warn "Service '$svc' absent from limits catalog (may be fine; verify manually)"
    fi
  done

  # Shape quota signal (compute). Exact limit names differ per tenancy;
  # list and grep rather than guessing one name.
  if [[ -n "$COMPARTMENT" ]]; then
    if QUOTAS=$(oci limits resource-availability list --compartment-id "$COMPARTMENT" \
                 --service-name compute --all --query 'data[?"availability-domain" != null]' 2>/dev/null); then
      E4=$(echo "$QUOTAS" | jq -r '[.[].name // empty] | map(select(test("e4-flex-core-count")))] | length' 2>/dev/null || echo 0)
      if [[ "$E4" != "0" ]]; then
        ok "E4 Flex core-count limits exist for this compartment"
      else
        warn "No E4-Flex limit rows returned — confirm OCPU quota in Console > Governance > Limits"
      fi
    else
      warn "Could not enumerate compute limits"
    fi
  fi
else
  warn "jq missing — skipping limits-catalog checks (install jq for full preflight)"
fi

# ------------------------------------------------- manual verification ----
cat <<'EOF'
Manual steps the CLI cannot verify reliably:
  * OKE VCN-native pod networking quota (Console > OKE)
  * Load Balancer quota (Flexible LB count/bandwidth)
  * Generative AI model access & region support (Console > Analytics & AI)
  * Vault secret-management quota
  * Database-with-PostgreSQL quota (system count/OCUs)
EOF

echo
echo "Summary: $PASS pass, $WARN warn, $FAIL fail"
[[ $FAIL -eq 0 ]]
