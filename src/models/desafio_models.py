from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
import datetime
from sqlmodel import SQLModel, Field



# ---------------------------
# Desafio
# ---------------------------
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
    created_at: str = Field(default=datetime.datetime.now().strftime('%Y-%m-%d'))

class DesafioResponse(BaseModel):
    id: int
    title: str
    desc: str

    class Config:
        from_attributes = True