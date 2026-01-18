.PHONY: run test docker-up docker-down minikube-start deploy monitoring port-forward smoke evidence down minikube-delete

run:
	uvicorn app.api.main:app --host 0.0.0.0 --port 8000

test:
	pytest -q

integration-test:
	RUN_INTEGRATION=1 docker compose up -d --build
	RUN_INTEGRATION=1 pytest -q tests/integration
	docker compose down

docker-up:
	docker compose up --build

docker-down:
	docker compose down

minikube-start:
	./scripts/minikube_start.sh

deploy:
	./scripts/deploy_migsec.sh

monitoring:
	./scripts/monitoring_install.sh

port-forward:
	./scripts/port_forward.sh all

smoke:
	./scripts/smoke_tests.sh

evidence:
	./scripts/collect_evidence.sh

down:
	kubectl delete namespace migsec monitoring --ignore-not-found

minikube-delete:
	minikube delete
