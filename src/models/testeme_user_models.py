from pydantic import BaseModel
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from typing import Optional

# ---------------------------
# Base User
# ---------------------------

class BaseUser(SQLModel):
    nome: str
    nick: str  

# Criar User include BaseUser
class SignUpUserRequest(BaseUser): 
    password: str

# Retorno dos dados
class UserData(BaseUser):
    score: float
    criacao_de_conta: datetime  # datetime UTC

# Include Users
class IncludeUser(BaseUser): 
    pass

# ---------------------------
# Tabela Users
# ---------------------------

class User(IncludeUser, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    criacao_de_conta: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    password: str
    score: float = Field(default=0.0)

# ---------------------------
# Login
# ---------------------------

class SignInUserRequest(SQLModel):
    nick: str
    password: str

class UpdateUserRequest(BaseModel):
    nome: Optional[str] = None
    nick: Optional[str] = None
    password: Optional[str] = None
