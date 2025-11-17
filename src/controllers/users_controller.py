from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from sqlmodel import Session, select
from sqlalchemy import or_
from sqlalchemy.sql import union_all

from src.database import get_engine

from src.models.users_models import SignInUserRequest, SignUpUserRequest, UserM, UpdateUserRequest, UserResponse

router = APIRouter()


# Lista os verbos disponiveis para esse controller
@router.options("", status_code=status.HTTP_200_OK)
async def options_Users():
    return { "methods": ["GET", "POST", "PATCH"] }

# Listar Users
@router.get("/", response_model=list[UserResponse])
def listar_Users():
    
    with Session(get_engine()) as session:
        statement = select(UserM)
        users = session.exec(statement).all()
        return [UserResponse.model_validate(u) for u in users]
        
        
        
# Cadastro de Users
@router.post('/cadastrar', status_code=status.HTTP_201_CREATED)
async def cadastrar_users(user_data: SignUpUserRequest):
    with Session(get_engine()) as session:

        # Verifica se já existe um admin, revendedor ou user com o código de confirmação de e-mail
        sttm = union_all(
            select(UserM.token).where(UserM.token == user_data.token),
        )
        registro_existente = session.exec(sttm).first()

        if registro_existente:
            raise HTTPException(
                status_code=status.HTTP_200_OK,
                detail='Token Já cadastrado'
            )

        # Criação do usuário
        user = UserM(
            token=user_data.token
        )


        if user:
            session.add(user)
            session.commit()
            session.refresh(user)

            return {"detail": "Token Cadastrado com sucesso."}

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao casatrar token."
        )