.PHONY: run test docker-up docker-down

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
