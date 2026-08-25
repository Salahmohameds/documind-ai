#!/usr/bin/env bash
# Inventory of existing resources in the target compartment before apply.
# Purpose: avoid naming collisions, duplicates and accidentally touching
# unrelated resources.
#
# Output: artifacts/inventory-<timestamp>.json (gitignored) + console summary.
# Usage: ./scripts/inventory.sh [--compartment <ocid>]

set -euo pipefail

COMPARTMENT="${OCI_COMPARTMENT_OCID:-}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --compartment) COMPARTMENT="$2"; shift 2 ;;
    *) echo "unknown arg: $1"; exit 2 ;;
  esac
done
[[ -z "$COMPARTMENT" ]] && { echo "set --compartment or OCI_COMPARTMENT_OCID"; exit 2; }

OUT_DIR="artifacts"
mkdir -p "$OUT_DIR"
TS=$(date +%Y%m%d-%H%M%S)
OUT="$OUT_DIR/inventory-$TS.json"
TMP=$(mktemp -d)

grab() { # grab <name> <cli args...>   (--compartment-id appended automatically)
  local name="$1"; shift
  echo "[..] $name"
  oci "$@" --compartment-id "$COMPARTMENT" --all --query 'data' -r \
      >"$TMP/$name.json" 2>"$TMP/$name.err" || true
}

grab vcns           network vcn list
grab subnets        network subnet list
grab nsgs           network nsg list
grab route-tables   network route-table list
grab security-lists network security-list list
grab public-ips     network public-ip list
grab clusters       containerengine cluster list
grab node-pools     containerengine node-pool list
grab load-balancers load-balancer load-balancer list
grab instances      compute instance list
grab buckets        os bucket list
grab psql-systems   psql db-system list
grab vaults         kms vault list

{
  echo '{'
  first=1
  for f in "$TMP"/*.json; do
    name=$(basename "$f" .json)
    [[ $first -eq 0 ]] && echo ','
    first=0
    printf ' "%s": ' "$name"
    cat "$f"
  done
  echo '}'
} > "$OUT"

echo
echo "Wrote $OUT"
echo "Non-empty sections:"
jq -r 'to_entries[] | select((.value | length) > 0) | "  \(.key): \(.value | length)"' "$OUT" || true
