import os

ENV = os.getenv("ENV", "development")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/mydb")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

CORS_ORIGINS = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]