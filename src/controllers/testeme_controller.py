from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import Annotated
from sqlalchemy.sql import union_all
from datetime import datetime

from src.database import get_engine
from src.models.desafio_models import CreateDesafioRequest, DesafioResponse, Desafio, UpdateDesafioRequest
from src.models.score_models import Score, UpdateScoreRequest, ScoreResponse

router = APIRouter()


# -----------------------------
# DESAFIOS
# -----------------------------

# Lista os verbos disponíveis
@router.options("/desafios", status_code=status.HTTP_200_OK)
async def options_desafios():
    return {"methods": ["GET", "POST", "PUT"]}

# Listar todos os desafios
@router.get("/desafios", response_model=list[DesafioResponse])
def listar_desafios():
    with Session(get_engine()) as session:
        statement = select(Desafio)
        desafios = session.exec(statement).all()
        return [DesafioResponse.model_validate(d) for d in desafios]

# Criar novo desafio
@router.post("/desafios", status_code=status.HTTP_201_CREATED)
def criar_desafio(desafio_data: CreateDesafioRequest):
    with Session(get_engine()) as session:
        desafio = Desafio(
            title=desafio_data.title,
            desc=desafio_data.desc,
            created_at=datetime.utcnow()
        )
        session.add(desafio)
        session.commit()
        session.refresh(desafio)
        return DesafioResponse.model_validate(desafio)

# Atualizar desafio existente
@router.put("/desafios/{id}", response_model=DesafioResponse)
def atualizar_desafio(id: int, desafio_data: UpdateDesafioRequest):
    with Session(get_engine()) as session:
        desafio = session.get(Desafio, id)
        if not desafio:
            raise HTTPException(status_code=404, detail="Desafio não encontrado")

        if desafio_data.title:
            desafio.title = desafio_data.title
        if desafio_data.desc:
            desafio.desc = desafio_data.desc

        session.add(desafio)
        session.commit()
        session.refresh(desafio)
        return DesafioResponse.model_validate(desafio)


# -----------------------------
# SCORE
# -----------------------------

# Lista os verbos disponíveis
@router.options("/score", status_code=status.HTTP_200_OK)
async def options_score():
    return {"methods": ["GET", "PUT"]}

# Obter score
@router.get("/score", response_model=ScoreResponse)
def obter_score():
    with Session(get_engine()) as session:
        score = session.get(Score, 1)  # assumindo ID 1
        if not score:
            raise HTTPException(status_code=404, detail="Score não encontrado")
        return ScoreResponse.model_validate(score)

# Atualizar score
@router.put("/score", response_model=ScoreResponse)
def atualizar_score(score_data: UpdateScoreRequest):
    with Session(get_engine()) as session:
        score = session.get(Score, 1)  # assumindo ID 1
        if not score:
            raise HTTPException(status_code=404, detail="Score não encontrado")

        if score_data.value is not None:
            score.value = score_data.value
            score.updated_at = datetime.utcnow()

        session.add(score)
        session.commit()
        session.refresh(score)
        return ScoreResponse.model_validate(score)
