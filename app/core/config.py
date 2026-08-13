import os
from typing import List

class Settings:
    PROJECT_NAME: str = "Multilingual PDF Triage & Text Extractor"
    VERSION: str = "1.0.0"
    
    # 500 MB Max File Upload Limit
    MAX_UPLOAD_SIZE_BYTES: int = 500 * 1024 * 1024
    
    # Session Management
    MAX_SESSIONS: int = 50
    
    # Allowed CORS Origins (restrict in production environment)
    CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
    ]

settings = Settings()
