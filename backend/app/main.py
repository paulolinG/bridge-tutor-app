from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import certification, health, microtopics, tutors
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="Bridge AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(microtopics.router)
app.include_router(certification.router)
app.include_router(tutors.router)
