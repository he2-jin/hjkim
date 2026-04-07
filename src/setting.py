import os
import secrets

# App
APP_NAME: str = "KakaoTalk-Clone"
APP_VERSION: str = "0.1.0"
HOST_NAME: str = "127.0.0.1"
PORT: int = 8000
DEBUG: bool = os.environ.get("DEBUG", "1") == "1"

# Database (MariaDB)
DB_HOST: str = os.environ.get("DB_HOST", "127.0.0.1")
DB_PORT: int = int(os.environ.get("DB_PORT", "3306"))
DB_USER: str = os.environ.get("DB_USER", "root")
DB_PASSWORD: str = os.environ.get("DB_PASSWORD", "")
DB_NAME: str = os.environ.get("DB_NAME", "kakaotalk")

DATABASE_URL: str = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    "?charset=utf8mb4"
)

# Redis
REDIS_HOST: str = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT: int = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB: int = int(os.environ.get("REDIS_DB", "0"))
REDIS_PASSWORD: str = os.environ.get("REDIS_PASSWORD", "")

# JWT
SECRET_KEY: str = os.environ.get("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
REFRESH_TOKEN_EXPIRE_DAYS: int = 14

# CORS
ORIGINS: list = [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]

# File Upload
UPLOAD_DIRECTORY: str = os.environ.get("UPLOAD_DIR", "./uploads")
MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

# Logging
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "DEBUG")
