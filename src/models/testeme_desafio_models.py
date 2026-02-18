from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel
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

    # ✅ Indica se a recompensa já foi coletada
    coletado: bool = Field(default=False, nullable=False)


class DesafioResponse(BaseModel):
    id: int
    title: str
    desc: str
    created_at: datetime
    coletado: bool

    class Config:
        from_attributes = True
