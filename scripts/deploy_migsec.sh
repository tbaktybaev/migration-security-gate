#!/usr/bin/env bash
set -euo pipefail

kubectl apply -f k8s/migsec/namespace.yaml
kubectl apply -f k8s/migsec

if command -v minikube >/dev/null 2>&1; then
  current_context="$(kubectl config current-context || true)"
  if [[ "$current_context" == "minikube" ]]; then
    eval "$(minikube docker-env)"
    docker build -t security-gate:latest .
  fi
fi

kubectl -n migsec rollout status deployment/minio --timeout=120s
kubectl -n migsec rollout status deployment/security-gate --timeout=120s
