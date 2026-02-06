import os
from fastapi.security import HTTPBearer

ENV = os.getenv("ENV", "development")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/mydb",
)

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

CORS_ORIGINS = [
    x.strip()
    for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if x.strip()
]

INITIAL_ADMIN_USERNAME = os.getenv("INITIAL_ADMIN_USERNAME")
INITIAL_ADMIN_PASSWORD = os.getenv("INITIAL_ADMIN_PASSWORD")

security = HTTPBearer()