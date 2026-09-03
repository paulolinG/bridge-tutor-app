from functools import lru_cache

import instructor
from anthropic import AsyncAnthropic

from app.core.config import get_settings


@lru_cache
def get_anthropic_client() -> AsyncAnthropic:
    return AsyncAnthropic(api_key=get_settings().anthropic_api_key)


@lru_cache
def get_instructor_client() -> instructor.AsyncInstructor:
    return instructor.from_anthropic(get_anthropic_client())
