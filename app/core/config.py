import os


API_TOKEN = os.getenv("API_TOKEN", "dev-token")
AUDIT_LOG_PATH = os.getenv("AUDIT_LOG_PATH", "data/audit.log")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "mig-artifacts")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
