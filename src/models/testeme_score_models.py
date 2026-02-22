from typing import Optional
from pydantic import BaseModel, field_validator, field_serializer
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field

# ---------------------------
# Score
# ---------------------------

class BaseScore(SQLModel):
    nick: str
    value: int


class CreateScoreRequest(BaseScore):
    pass


class UpdateScoreRequest(BaseModel):
    value: Optional[int] = None


class Score(BaseScore, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # 🔒 Sempre salva em UTC+00
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # 🔒 Se banco devolver naive, assume UTC
    @field_validator("updated_at", mode="before")
    @classmethod
    def force_utc(cls, value):
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return value


class ScoreResponse(BaseModel):
    id: int
    value: int
    updated_at: datetime

    class Config:
        from_attributes = True

    # 🔥 Sempre retorna ISO UTC com Z
    @field_serializer("updated_at")
    def serialize_updated_at(self, value: datetime):
        return (
            value
            .astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )