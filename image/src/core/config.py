import os

class Settings:
    table_name: str = os.getenv("TABLE_NAME", "default_table")
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    worker_lambda_name: str = os.getenv("WORKER_LAMBDA_NAME", "local_worker_lambda")

settings = Settings()
