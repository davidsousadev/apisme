import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timedelta, timezone
from typing import Annotated
from sqlmodel import Session, select
from passlib.context import CryptContext

from src.database import get_engine
from src.auth_utils import (
    get_logged_user,
    hash_password,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_EXPIRES,
    REFRESH_EXPIRES
)

from src.models.testeme_user_models import (
    SignInUserRequest,
    SignUpUserRequest,
    User
)

from src.models.testeme_desafio_models import (
    CreateDesafioRequest,
    DesafioResponse,
    Desafio
)

from src.models.testeme_operacoes_models import (
    Operacoes,
    OperacoesResponse
)

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# =============================
# USERS
# =============================

@router.post('/cadastrar', status_code=status.HTTP_201_CREATED)
async def cadastrar_users(user_data: SignUpUserRequest):
    with Session(get_engine()) as session:
        user_exists = session.exec(
            select(User).where(User.nick == user_data.nick)
        ).first()

        if user_exists:
            raise HTTPException(status_code=400, detail='Nick já cadastrado!')

        user = User(
            nome=user_data.nome,
            nick=user_data.nick,
            password=hash_password(user_data.password),
            score=0
        )

        session.add(user)
        session.commit()

        return {"detail": "Usuário cadastrado com sucesso!"}


@router.post('/logar')
def logar_users(signin_data: SignInUserRequest):
    with Session(get_engine()) as session:
        user = session.exec(
            select(User).where(User.nick == signin_data.nick)
        ).first()

        if not user:
            raise HTTPException(status_code=400, detail='Nick inválido!')

        if not pwd_context.verify(signin_data.password, user.password):
            raise HTTPException(status_code=400, detail='Senha incorreta!')

        agora = datetime.now(timezone.utc)

        access_expires = agora + timedelta(minutes=ACCESS_EXPIRES)
        refresh_expires = agora + timedelta(minutes=REFRESH_EXPIRES)

        access_token = jwt.encode({'sub': user.nick, 'exp': access_expires}, SECRET_KEY, algorithm=ALGORITHM)
        refresh_token = jwt.encode({'sub': user.nick, 'exp': refresh_expires}, SECRET_KEY, algorithm=ALGORITHM)

        return {'access_token': access_token, 'refresh_token': refresh_token}


@router.get("/autenticar")
def autenticar_users(user: Annotated[User, Depends(get_logged_user)]):
    return user


# =============================
# DESAFIOS
# =============================

@router.get("/desafios", response_model=list[DesafioResponse])
def listar_desafios():
    with Session(get_engine()) as session:
        desafios = session.exec(select(Desafio)).all()
        return [DesafioResponse.model_validate(d) for d in desafios]


@router.post("/desafios", response_model=DesafioResponse, status_code=status.HTTP_201_CREATED)
def criar_desafio(desafio_data: CreateDesafioRequest):
    with Session(get_engine()) as session:
        desafio = Desafio(
            title=desafio_data.title,
            desc=desafio_data.desc
            # created_at já é UTC timezone-aware pelo model
        )

        session.add(desafio)
        session.commit()
        session.refresh(desafio)

        return DesafioResponse.model_validate(desafio)


# =============================
# COLETAR RECOMPENSA
# =============================

@router.post("/desafios/{id}/coletar")
def coletar_recompensa(
    id: int,
    user: Annotated[User, Depends(get_logged_user)]
):
    with Session(get_engine()) as session:
        desafio = session.get(Desafio, id)

        if not desafio:
            raise HTTPException(status_code=404, detail="Desafio não encontrado")

        # 🚫 Impede coleta duplicada
        if desafio.coletado:
            raise HTTPException(status_code=400, detail="Recompensa já coletada.")

        # 🔒 Garantia absoluta de UTC
        if desafio.created_at.tzinfo is None:
            raise HTTPException(
                status_code=500,
                detail="Erro interno: created_at não é timezone-aware"
            )

        agora = datetime.now(timezone.utc)

        # ✅ Cálculo direto (UTC - UTC)
        tempo_passado = (agora - desafio.created_at).total_seconds()

        # 🔒 Proteção contra valores negativos (clock skew)
        if tempo_passado < 0:
            tempo_passado = 0

        # 🚫 Expirou após 240 segundos
        if tempo_passado >= 240:
            raise HTTPException(
                status_code=400,
                detail="Tempo expirado! Nenhuma recompensa disponível."
            )

        # 🎯 Pontuação linear (100 → 0)
        pontos = int(100 * (1 - (tempo_passado / 240)))
        pontos = max(pontos, 0)

        # Atualiza usuário
        db_user = session.exec(
            select(User).where(User.nick == user.nick)
        ).first()

        if not db_user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")

        db_user.score += pontos
        desafio.coletado = True

        # Registrar operação
        nova_operacao = Operacoes(
            nick=user.nick,
            valor=pontos,
            tipo="recompensa",
            descricao=f"Recompensa do desafio {desafio.title}",
            created_at=datetime.now(timezone.utc)
        )

        session.add_all([nova_operacao, db_user, desafio])
        session.commit()

        return {
            "message": "Recompensa coletada com sucesso!",
            "pontos_ganhos": pontos,
            "novo_score": db_user.score,
            "tempo_passado_segundos": int(tempo_passado)
        }


# =============================
# OPERACOES
# =============================

@router.get("/operacoes", response_model=list[OperacoesResponse])
def listar_operacoes(
    nick: str,
    user: Annotated[User, Depends(get_logged_user)]
):
    if nick != user.nick:
        raise HTTPException(status_code=403, detail="Você não pode acessar operações de outro usuário")

    with Session(get_engine()) as session:
        operacoes = session.exec(
            select(Operacoes)
            .where(Operacoes.nick == nick)
            .order_by(Operacoes.created_at.desc())
        ).all()

        return [OperacoesResponse.model_validate(op) for op in operacoes]
