from pydantic import BaseModel, Field
from datetime import datetime
import datetime
from sqlmodel import SQLModel, Field



class BaseUser(SQLModel):
  token: str

# Criar User include BaseUser
class SignUpUserRequest(BaseUser): 
  pass

# Retorno dos dados
class UserData(BaseUser):
  pass

# Include Users
class IncludeUser(BaseUser): 
  pass


# Tabela Users  
class User(IncludeUser, table=True):
  id: int = Field(default=None, primary_key=True)

# Login
class SignInUserRequest(SQLModel):
  pass

class UpdateUserRequest(BaseModel):
    pass

# Lista de usuarios
class UserResponse(BaseModel):
    id: int
    token: str

    class Config:
        from_attributes = True