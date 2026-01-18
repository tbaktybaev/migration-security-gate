# Migration Security Gate

## Overview
Control-plane service that validates migration artifacts and returns ALLOW/BLOCK decisions before deployment or replication. This system protects the migration phase, not runtime.

## Project Structure
```
app/
  api/main.py       - FastAPI application with endpoints
  audit/logger.py   - Audit logging functionality
  core/             - Core models, config, security, utils
  integrity/        - Artifact hashing and integrity checks
  policies/         - Policy engine
  validators/       - Migration and replication validators
  ui/
    static/         - CSS and static assets
    templates/      - Jinja2 HTML templates
data/               - Audit log storage
examples/           - Example artifacts for testing
tests/              - Unit and integration tests
```

## Technology Stack
- Python 3.11
- FastAPI web framework
- Pydantic for data validation
- Jinja2 for HTML templating
- MinIO for object storage (optional, for reference mode)

## Running the Application
The application runs on port 5000 using uvicorn:
```
uvicorn app.api.main:app --host 0.0.0.0 --port 5000
```

## Environment Variables
- `API_TOKEN` (default: `dev-token`) - Bearer token for API authentication
- `AUDIT_LOG_PATH` (default: `data/audit.log`) - Audit log file location
- `MINIO_ENDPOINT` - MinIO server endpoint (for reference mode)
- `MINIO_ACCESS_KEY` - MinIO access key
- `MINIO_SECRET_KEY` - MinIO secret key
- `MINIO_BUCKET` - MinIO bucket name
- `MINIO_SECURE` - Use HTTPS for MinIO

## UI Routes
- `/` - Home/menu page
- `/ui/migration` - Migration validation form
- `/ui/replication` - Replication validation form
- `/ui/audit` - View audit logs
- `/ui/alerts` - View blocked validations

## API Endpoints
- `POST /api/v1/validate/migration` - Validate migration artifacts
- `POST /api/v1/validate/replication` - Validate replication artifacts
- `POST /api/v1/validate/replication/ref` - Validate via reference
- `GET /api/v1/audit/logs` - Retrieve audit logs

## Testing
```
pytest -q
```
