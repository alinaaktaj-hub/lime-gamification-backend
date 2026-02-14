import os
from dotenv import load_dotenv
from fastapi.security import HTTPBearer

_DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173,"
    "http://localhost:5174,"
    "http://127.0.0.1:5173,"
    "http://127.0.0.1:5174"
)

load_dotenv()

ENV = os.getenv("ENV", "development")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/mydb",
)

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

CORS_ORIGINS = [
    x.strip().rstrip("/")
    for x in os.getenv("CORS_ORIGINS", _DEFAULT_CORS_ORIGINS).split(",")
    if x.strip()
]

INITIAL_ADMIN_USERNAME = os.getenv("INITIAL_ADMIN_USERNAME")
INITIAL_ADMIN_PASSWORD = os.getenv("INITIAL_ADMIN_PASSWORD")

security = HTTPBearer()
