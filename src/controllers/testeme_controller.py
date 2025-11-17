import jwt
import string
import random

from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from typing import Annotated
from sqlmodel import Session, select

from src.database import get_engine
from src.auth_utils import get_logged_user, hash_password, SECRET_KEY, ALGORITHM, ACCESS_EXPIRES, REFRESH_EXPIRES

from src.models.testeme_user_models import SignInUserRequest, SignUpUserRequest, User, UpdateUserRequest

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import Annotated
from sqlalchemy.sql import union_all
from datetime import datetime

from src.database import get_engine
from src.models.testeme_desafio_models import CreateDesafioRequest, DesafioResponse, Desafio, UpdateDesafioRequest
from src.models.testeme_operacoes_models import Operacoes, CreateOperacaoRequest, OperacoesResponse

router = APIRouter()

# -----------------------------
# Users
# -----------------------------

# Gera codigo com 6 caracteres para confirmação
def gerar_codigo_confirmacao(tamanho=6):
        """Gera um código aleatório de confirmação."""
        caracteres = string.ascii_letters + string.digits
        return ''.join(random.choices(caracteres, k=tamanho))
 
# Cadastro de Users
@router.post('/cadastrar', status_code=status.HTTP_201_CREATED)
async def cadastrar_users(user_data: SignUpUserRequest):
    with Session(get_engine()) as session:

        # Verifica se já existe um User com o mesmo nick
        sttm = select(User.nick).where(User.nick == user_data.nick)
        nick_existente = session.exec(sttm).first()

        if nick_existente:
            raise HTTPException(
                status_code=status.HTTP_200_OK,
                detail='Nick já cadastrado anteriormente!'
            )

        # Hash da senha
        hash = hash_password(user_data.password)       

        # Criação do usuário e user
        user = User(
            nome=user_data.nome,
            nick=user_data.nick, 
            score=0,
            password=hash
        )
    
        session.add(user)
        session.commit()
        session.refresh(user)
        
        return {"detail": "Usuário cadastrado com sucesso!"}

# Login de Users
@router.post('/logar')
def logar_Users(signin_data: SignInUserRequest):
  with Session(get_engine()) as session:
    # pegar usuário por nick
    
    sttm = select(User).where(User.nick == signin_data.nick)
    user = session.exec(sttm).first()
    
    if not user: # não encontrou usuário
      raise HTTPException(status_code=status.HTTP_200_OK, 
        detail='Nick invalido!')
    
    # encontrou, então verificar a senha
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    is_correct = pwd_context.verify(signin_data.password, user.password)

    if not is_correct:
      raise HTTPException(
        status_code=status.HTTP_200_OK, 
        detail='Senha incorrenta!')
    
    
    # Tá tudo OK pode gerar um Token JWT e devolver
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_EXPIRES)
    access_token = jwt.encode({'sub': user.nick, 'exp': expires_at}, key=SECRET_KEY, algorithm=ALGORITHM)

    expires_rt = datetime.now(timezone.utc) + timedelta(minutes=REFRESH_EXPIRES)
    refresh_token = jwt.encode({'sub': user.nick, 'exp': expires_rt}, key=SECRET_KEY, algorithm=ALGORITHM)
    
    return {'access_token': access_token, 'refresh_token': refresh_token}

# Autentica Users
@router.get("/autenticar")
def autenticar_Users(user: Annotated[User, Depends(get_logged_user)]):
  return user

# Atualiza Users
@router.patch("/atualizar", status_code=status.HTTP_200_OK)
def atualizar_Users_por(
    user_data: UpdateUserRequest, 
    user: Annotated[User, Depends(get_logged_user)]):
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail="Acesso negado!"
        )

    with Session(get_engine()) as session:
        sttm = select(User).where(User.id == user.id)
        user_to_update = session.exec(sttm).first()

        if not user_to_update:
            raise HTTPException(
                status_code=status.HTTP_200_OK,
                detail="Usuário não encontrado."
            )

        # Atualizar os campos fornecidos
        if user_data.nome and user_to_update.nome != user_data.nome:
            user_to_update.nome = user_data.nome           
        if user_data.nick and user_to_update.nick != user_data.nick:
            # Verifica se já existe um admin, revendedor ou User com o código de confirmação de e-mail
            sttm = select(User).where(User.nick == user_data.nick
            )
            registro_existente = session.exec(sttm).first()

            if registro_existente:
                raise HTTPException(
                    status_code=status.HTTP_200_OK,
                    detail='Nick já cadastrado anteriormente. Tente recuperar o nick!'
                )

        if user_data.password and user_to_update.password != hash_password(user_data.password):
            user_to_update.password = hash_password(user_data.password)
            
        # Salvar as alterações no banco de dados
        session.add(user_to_update)
        session.commit()
        session.refresh(user_to_update)

        return {"message": "Usuário atualizado com sucesso!", "user": user_to_update}

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

@router.options("/operacoes", status_code=status.HTTP_200_OK)
async def options_score():
    return {"methods": ["GET", "POST"]}

@router.get("/operacoes", response_model=list[OperacoesResponse])
def listar_operacoes(nick: str, user: Annotated[User, Depends(get_logged_user)]):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail="Acesso negado!"
        )
    with Session(get_engine()) as session:

        sttm = (
            select(Operacoes)
            .where(Operacoes.nick == nick)
            .order_by(Operacoes.created_at.desc())
        )

        operacoes = session.exec(sttm).all()
        if not operacoes:
            raise HTTPException(status_code=200, detail="Nenhuma operacão encontrada!")
        
        return [OperacoesResponse.model_validate(op) for op in operacoes]


@router.post("/operacoes", response_model=OperacoesResponse, status_code=201)
def criar_operacao(operacao: CreateOperacaoRequest, user: Annotated[User, Depends(get_logged_user)]):

    if not user:
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail="Acesso negado!"
        )

    with Session(get_engine()) as session:

        # Buscar o usuário
        sttm = select(User).where(User.nick == operacao.nick)
        user = session.exec(sttm).first()

        if not user:
            raise HTTPException(status_code=200, detail="Usuário não encontrado")

        # Criar operação
        nova_op = Operacoes(
            nick=operacao.nick,
            valor=operacao.valor,
            tipo=operacao.tipo,
            descricao=operacao.descricao
        )
        session.add(nova_op)

        # Atualizar score total do usuário
        user.score += operacao.valor
        session.add(user)

        # Salvar tudo
        session.commit()
        session.refresh(nova_op)

        return OperacoesResponse.model_validate(nova_op)
