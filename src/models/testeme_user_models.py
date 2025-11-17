from pydantic import BaseModel, Field
from datetime import datetime
import datetime
from sqlmodel import SQLModel, Field


    
class BaseUser(SQLModel):
  nome: str
  nick: str  

# Criar User include BaseUser
class SignUpUserRequest(BaseUser): 
  password: str
    
# Retorno dos dados
class UserData(BaseUser):
  score: int
  
# Include Users
class IncludeUser(BaseUser): 
  pass
  
# Tabela Users  
class User(IncludeUser, table=True):
  id: int = Field(default=None, primary_key=True)
  criacao_de_conta: str = Field(default=datetime.datetime.now().strftime('%Y-%m-%d'))
  password: str
  score: float
  
# Login
class SignInUserRequest(SQLModel):
  nick: str
  password: str

class UpdateUserRequest(BaseModel):
    nome: str | None = None
    nick: str | None = None
    password: str | None = None
