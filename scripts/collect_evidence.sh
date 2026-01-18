#!/usr/bin/env bash
set -euo pipefail

STAMP=$(date +"%Y%m%d_%H%M%S")
OUT_DIR="evidence/${STAMP}"
mkdir -p "${OUT_DIR}"

kubectl get pods -n migsec > "${OUT_DIR}/pods_migsec.txt"
kubectl get pods -n monitoring > "${OUT_DIR}/pods_monitoring.txt"

kubectl get svc -n migsec > "${OUT_DIR}/svc_migsec.txt"
kubectl get svc -n monitoring > "${OUT_DIR}/svc_monitoring.txt"

kubectl logs -n migsec deployment/security-gate --tail=200 > "${OUT_DIR}/security_gate_logs.txt"

kubectl describe servicemonitor -n monitoring security-gate > "${OUT_DIR}/servicemonitor_security_gate.txt" || true

echo "Evidence saved to ${OUT_DIR}"
