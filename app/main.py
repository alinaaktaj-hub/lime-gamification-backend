from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.database import lifespan
from app.api import (
    auth_router,
    chat_test_router,
    student_router,
    teacher_router,
    admin_router,
    public_router,
)

app = FastAPI(title="Lime Gamification", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(chat_test_router.router)
app.include_router(student_router.router)
app.include_router(teacher_router.router)
app.include_router(admin_router.router)
app.include_router(public_router.router)