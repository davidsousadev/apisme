import os
import re
import unicodedata
from typing import Iterable

from decouple import config
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from src.database import get_engine
from src.models.aluno_models import (
    Aluno, VincularAlunoRequest, CadastrarAlunoRequest,
    ImportarAlunosRequest,
)

router = APIRouter()


def normalizar_texto(valor: str) -> str:
    """Normaliza espaços, acentos e caixa para comparar nomes sem diferenciar acentos."""
    valor = unicodedata.normalize("NFKD", valor.strip())
    valor = "".join(ch for ch in valor if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", valor).casefold()


def normalizar_matricula(valor: str) -> str:
    return re.sub(r"\s+", "", valor).upper()


def validar_admin(x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")):
    segredo = config("ALUNOS_ADMIN_TOKEN", default="")
    if not segredo:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cadastro administrativo de alunos não está configurado no servidor.",
        )
    if not x_admin_token or x_admin_token != segredo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credencial administrativa inválida.")


def aluno_publico(aluno: Aluno) -> dict:
    return {"id": aluno.id, "matricula": aluno.matricula, "nome_completo": aluno.nome_completo}


@router.post("/vincular", status_code=status.HTTP_200_OK)
def vincular_aluno(dados: VincularAlunoRequest):
    """Confirma matrícula + nome contra a tabela oficial de alunos ativos."""
    matricula = normalizar_matricula(dados.matricula)
    nome = normalizar_texto(dados.nome_completo)
    if not matricula or not nome:
        raise HTTPException(status_code=422, detail="Informe a matrícula e o nome completo do aluno.")

    with Session(get_engine()) as session:
        aluno = session.exec(select(Aluno).where(Aluno.matricula == matricula)).first()
        # Mensagem genérica para não revelar se uma matrícula existe.
        if not aluno or not aluno.ativo or normalizar_texto(aluno.nome_completo) != nome:
            raise HTTPException(status_code=404, detail="Não foi possível confirmar os dados informados. Verifique a matrícula e o nome completo com a escola.")
        return {
            "success": True,
            "message": "Aluno validado com sucesso.",
            "aluno": aluno_publico(aluno),
        }


@router.post("/cadastrar", status_code=status.HTTP_201_CREATED, dependencies=[Depends(validar_admin)])
def cadastrar_aluno(dados: CadastrarAlunoRequest):
    """Cadastra um aluno oficial. Requer X-Admin-Token configurado no servidor."""
    matricula = normalizar_matricula(dados.matricula)
    nome = re.sub(r"\s+", " ", dados.nome_completo.strip())
    if not matricula or not nome:
        raise HTTPException(status_code=422, detail="Matrícula e nome completo são obrigatórios.")
    with Session(get_engine()) as session:
        existente = session.exec(select(Aluno).where(Aluno.matricula == matricula)).first()
        if existente:
            raise HTTPException(status_code=409, detail="Já existe um aluno cadastrado com essa matrícula.")
        aluno = Aluno(matricula=matricula, nome_completo=nome, ativo=dados.ativo)
        session.add(aluno)
        try:
            session.commit()
            session.refresh(aluno)
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail="Já existe um aluno cadastrado com essa matrícula.")
        return {"success": True, "message": "Aluno cadastrado com sucesso.", "aluno": aluno_publico(aluno)}


@router.post("/importar", status_code=status.HTTP_200_OK, dependencies=[Depends(validar_admin)])
def importar_alunos(dados: ImportarAlunosRequest):
    """Importa uma lista de alunos; atualiza nome/ativo se a matrícula já existir."""
    criados = 0
    atualizados = 0
    with Session(get_engine()) as session:
        for item in dados.alunos:
            matricula = normalizar_matricula(item.matricula)
            nome = re.sub(r"\s+", " ", item.nome_completo.strip())
            if not matricula or not nome:
                continue
            aluno = session.exec(select(Aluno).where(Aluno.matricula == matricula)).first()
            if aluno:
                aluno.nome_completo = nome
                aluno.ativo = item.ativo
                atualizados += 1
            else:
                session.add(Aluno(matricula=matricula, nome_completo=nome, ativo=item.ativo))
                criados += 1
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail="Não foi possível importar a lista por conflito de matrículas.")
    return {"success": True, "message": "Importação concluída.", "criados": criados, "atualizados": atualizados, "total_recebido": len(dados.alunos)}


@router.get("/health", status_code=status.HTTP_200_OK)
def health_alunos():
    return {"success": True, "service": "alunos", "message": "Serviço de alunos disponível."}
