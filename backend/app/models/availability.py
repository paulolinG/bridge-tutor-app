from pydantic import BaseModel, Field, model_validator

MIN_MINUTE_OF_DAY: int = 0
MAX_MINUTE_OF_DAY: int = 1440


class AvailabilityWindowInput(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start_minute: int = Field(ge=MIN_MINUTE_OF_DAY, le=MAX_MINUTE_OF_DAY)
    end_minute: int = Field(ge=MIN_MINUTE_OF_DAY, le=MAX_MINUTE_OF_DAY)

    @model_validator(mode="after")
    def check_start_before_end(self) -> "AvailabilityWindowInput":
        if self.start_minute >= self.end_minute:
            raise ValueError("start_minute must be before end_minute")
        return self


class UpdateAvailabilityRequest(BaseModel):
    windows: list[AvailabilityWindowInput]
    daily_cap_minutes: int = Field(gt=0)
    weekly_cap_minutes: int = Field(gt=0)


class AvailabilityResponse(BaseModel):
    windows: list[AvailabilityWindowInput]
    daily_cap_minutes: int | None
    weekly_cap_minutes: int | None
