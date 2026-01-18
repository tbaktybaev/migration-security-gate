#!/usr/bin/env bash
set -euo pipefail

mode=${1:-all}

forward_gate() {
  kubectl -n migsec port-forward svc/security-gate 8000:8000
}

forward_grafana() {
  kubectl -n monitoring port-forward svc/kube-prometheus-stack-grafana 3000:80
}

forward_prometheus() {
  kubectl -n monitoring port-forward svc/kube-prometheus-stack-prometheus 9090:9090
}

case "$mode" in
  gate)
    forward_gate
    ;;
  grafana)
    forward_grafana
    ;;
  prometheus)
    forward_prometheus
    ;;
  all)
    forward_gate &
    forward_grafana &
    forward_prometheus &
    wait
    ;;
  *)
    echo "Usage: $0 {gate|grafana|prometheus|all}" >&2
    exit 1
    ;;
esac
