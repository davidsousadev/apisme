from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel, field_validator, field_serializer


# ============================
# OPERACOES (UTC 00 GLOBAL)
# ============================

class Operacoes(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    nick: str = Field(index=True)
    valor: int
    tipo: str
    descricao: Optional[str] = None

    # 🔒 Sempre salva em UTC+00
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # 🔒 Se banco devolver naive, assume UTC
    @field_validator("created_at", mode="before")
    @classmethod
    def force_utc(cls, value):
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return value


# ============================
# REQUEST
# ============================

class CreateOperacaoRequest(BaseModel):
    nick: str
    valor: int
    tipo: str
    descricao: Optional[str] = None


# ============================
# RESPONSE
# ============================

class OperacoesResponse(BaseModel):
    id: int
    nick: str
    valor: int
    tipo: str
    descricao: Optional[str]
    created_at: datetime

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