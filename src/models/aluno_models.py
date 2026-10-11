from typing import Optional
from sqlmodel import SQLModel, Field
from pydantic import BaseModel, Field as PydanticField


class Aluno(SQLModel, table=True):
    """Cadastro oficial de alunos usado para validar o vínculo no CEMAB App."""
    id: Optional[int] = Field(default=None, primary_key=True)
    matricula: str = Field(index=True, unique=True, max_length=40)
    nome_completo: str = Field(max_length=160)
    ativo: bool = Field(default=True, index=True)


class VincularAlunoRequest(BaseModel):
    matricula: str = PydanticField(min_length=1, max_length=40)
    nome_completo: str = PydanticField(min_length=3, max_length=160)


class CadastrarAlunoRequest(BaseModel):
    matricula: str = PydanticField(min_length=1, max_length=40)
    nome_completo: str = PydanticField(min_length=3, max_length=160)
    ativo: bool = True


class ImportarAlunosRequest(BaseModel):
    alunos: list[CadastrarAlunoRequest] = PydanticField(min_length=1, max_length=5000)


class AlunoVinculadoResponse(BaseModel):
    success: bool = True
    message: str
    aluno: dict
