#!/usr/bin/env bash
set -euo pipefail

for cmd in minikube kubectl docker; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
done

minikube start --cpus=4 --memory=5096 --disk-size=20g --driver=docker

minikube status
