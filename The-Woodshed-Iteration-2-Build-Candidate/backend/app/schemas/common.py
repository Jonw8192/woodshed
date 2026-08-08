from pydantic import BaseModel, Field


class LeagueRef(BaseModel):
    league_id: str = Field(pattern=r"^\d{8,25}$")


class HealthResponse(BaseModel):
    ok: bool
    service: str
    version: str
