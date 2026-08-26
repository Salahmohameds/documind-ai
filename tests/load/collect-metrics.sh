#!/usr/bin/env bash
# Sample cluster state during a load run.
#
# k6 measures the client side only. CPU, memory, pod count and HPA
# replicas are required by the role brief and by the monolith-vs-OKE
# comparison table, and none of them appear in k6 output — they have to
# be sampled from the cluster while the run is in flight.
#
# Read-only: this touches nothing in the cluster. It needs a kubeconfig
# with get/list on pods and hpa in the target namespace, nothing more.
#
# Usage:
#   ./collect-metrics.sh <label> [namespace] [interval_seconds]
#
# Run it in a second terminal, started just before k6 and stopped just
# after. Ctrl-C to finish.

set -uo pipefail

LABEL="${1:?usage: collect-metrics.sh <label> [namespace] [interval]}"
NAMESPACE="${2:-documind}"
INTERVAL="${3:-5}"

OUT_DIR="$(dirname "$0")/results"
mkdir -p "$OUT_DIR"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
CSV="${OUT_DIR}/${LABEL}_${STAMP}_cluster.csv"

echo "timestamp,pods_total,pods_ready,hpa_current,hpa_desired,cpu_millicores,memory_mib,restarts_total" > "$CSV"

echo "sampling namespace=${NAMESPACE} every ${INTERVAL}s -> ${CSV}"
echo "Ctrl-C to stop."

cleanup() {
  echo ""
  echo "stopped. $(( $(wc -l < "$CSV") - 1 )) samples written to ${CSV}"
  exit 0
}
trap cleanup INT TERM

while true; do
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  pods_json="$(kubectl get pods -n "$NAMESPACE" -o json 2>/dev/null)"
  if [ -z "$pods_json" ]; then
    echo "${ts},,,,,,," >> "$CSV"
    sleep "$INTERVAL"
    continue
  fi

  pods_total="$(echo "$pods_json" | jq '[.items[]] | length')"
  pods_ready="$(echo "$pods_json" | jq '[.items[] | select(.status.conditions[]? | select(.type=="Ready" and .status=="True"))] | length')"
  restarts="$(echo "$pods_json" | jq '[.items[].status.containerStatuses[]?.restartCount] | add // 0')"

  # metrics-server may not be installed; degrade to blank rather than fail
  top="$(kubectl top pods -n "$NAMESPACE" --no-headers 2>/dev/null)"
  if [ -n "$top" ]; then
    cpu="$(echo "$top" | awk '{gsub(/m$/,"",$2); s+=$2} END {print s+0}')"
    mem="$(echo "$top" | awk '{gsub(/Mi$/,"",$3); s+=$3} END {print s+0}')"
  else
    cpu=""
    mem=""
  fi

  hpa="$(kubectl get hpa -n "$NAMESPACE" -o json 2>/dev/null)"
  if [ -n "$hpa" ]; then
    hpa_cur="$(echo "$hpa" | jq '[.items[].status.currentReplicas] | add // 0')"
    hpa_des="$(echo "$hpa" | jq '[.items[].status.desiredReplicas] | add // 0')"
  else
    hpa_cur=""
    hpa_des=""
  fi

  echo "${ts},${pods_total},${pods_ready},${hpa_cur},${hpa_des},${cpu},${mem},${restarts}" >> "$CSV"
  sleep "$INTERVAL"
done