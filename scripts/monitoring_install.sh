#!/usr/bin/env bash
set -euo pipefail

if ! command -v helm >/dev/null 2>&1; then
  echo "Missing required command: helm" >&2
  exit 1
fi

kubectl apply -f k8s/monitoring/namespace.yaml

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace

kubectl -n monitoring rollout status deployment/kube-prometheus-stack-operator --timeout=120s || true

kubectl apply -f k8s/monitoring/servicemonitor-security-gate.yaml

echo "Grafana: kubectl -n monitoring port-forward svc/kube-prometheus-stack-grafana 3000:80"
echo "Prometheus: kubectl -n monitoring port-forward svc/kube-prometheus-stack-prometheus 9090:9090"
