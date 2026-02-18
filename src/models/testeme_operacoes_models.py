from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel

class Operacoes(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nick: str = Field(index=True)
    valor: int  # mudança: +10, -4, +20 etc.
    tipo: str   # ganho, perda, bonificação, punição...
    descricao: Optional[str] = None
    # ✅ Hora UTC timezone-aware
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CreateOperacaoRequest(BaseModel):
    nick: str
    valor: int     # mudança
    tipo: str
    descricao: Optional[str] = None


class OperacoesResponse(BaseModel):
    id: int
    nick: str
    valor: int
    tipo: str
    descricao: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
