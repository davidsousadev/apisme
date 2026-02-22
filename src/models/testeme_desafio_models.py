from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel, field_serializer, field_validator
from sqlmodel import SQLModel, Field


# ============================
# DESAFIO
# ============================

class BaseDesafio(SQLModel):
    title: str
    desc: str


class CreateDesafioRequest(BaseDesafio):
    pass


class UpdateDesafioRequest(BaseModel):
    title: Optional[str] = None
    desc: Optional[str] = None


class Desafio(BaseDesafio, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # ✅ Sempre UTC timezone-aware
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    coletado: bool = Field(default=False, nullable=False)

    @field_validator("created_at")
    @classmethod
    def ensure_timezone(cls, value: datetime):
        if value.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        return value


class DesafioResponse(BaseModel):
    id: int
    title: str
    desc: str
    created_at: datetime
    coletado: bool

    class Config:
        from_attributes = True

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")