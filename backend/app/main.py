from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    availability,
    certification,
    health,
    impact,
    join,
    matching,
    microtopics,
    sessions,
    tutors,
)
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
app.include_router(matching.router)
app.include_router(availability.router)
app.include_router(sessions.router)
app.include_router(join.router)
app.include_router(impact.router)
