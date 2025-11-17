from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import datetime
from pydantic import BaseModel

class Operacoes(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nick: str = Field(index=True)
    valor: int  # mudança: +10, -4, +20 etc.
    tipo: str   # ganho, perda, bonificação, punição...
    descricao: Optional[str] = None
    created_at: str = Field(default=datetime.datetime.now().strftime('%Y-%m-%d'))


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
    created_at: str = Field(default=datetime.datetime.now().strftime('%Y-%m-%d'))

    class Config:
        from_attributes = True
