from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel, field_serializer, field_validator
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime


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

    # ✅ FORÇA TIMESTAMP WITH TIME ZONE NO BANCO
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),  # 🔥 ESSENCIAL
            nullable=False,
            default=lambda: datetime.now(timezone.utc),
        )
    )

    coletado: bool = Field(default=False, nullable=False)

    # 🔒 Garantia extra caso o driver entregue naive
    @field_validator("created_at", mode="before")
    @classmethod
    def force_utc(cls, value):
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return value


class DesafioResponse(BaseModel):
    id: int
    title: str
    desc: str
    created_at: datetime
    coletado: bool

    class Config:
        from_attributes = True

    # 🔥 Sempre retorna ISO UTC com Z
    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime):
        return (
            value
            .astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )