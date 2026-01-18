#!/usr/bin/env bash
set -euo pipefail

kubectl apply -f k8s/migsec/namespace.yaml
kubectl apply -f k8s/migsec

kubectl -n migsec rollout status deployment/minio --timeout=120s
kubectl -n migsec rollout status deployment/security-gate --timeout=120s
