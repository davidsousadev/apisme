"""Webhook de presenças e histórico de notificações do CEMAB App.

A automação externa deve mandar eventos já tratados. Este módulo não lê nem
transforma arquivos/relatórios Control iD.
"""
import hashlib
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from decouple import config
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from firebase_admin import messaging
from sqlmodel import Session, select

from src.database import get_engine
from src.firebase_service import ensure_firebase_app
from src.models.aluno_models import (
    Aluno, AlunoDispositivo, EventoPresenca, EventoPresencaLoteRequest,
    EventoPresencaRequest,
)
from src.models.users_models import UserM
from src.controllers.alunos_controller import normalizar_matricula, localizar_aluno_por_matricula

router = APIRouter()
_BRASILIA = ZoneInfo("America/Brasilia")


def validar_token_eventos(x_cemab_event_token: str | None = Header(default=None, alias="X-CEMAB-Event-Token")):
    segredo = config("CEMAB_EVENT_TOKEN", default="").strip() or config("PRESENCA_WEBHOOK_TOKEN", default="").strip()
    if not segredo:
        raise HTTPException(status_code=503, detail="Webhook de presenças não está configurado no servidor.")
    if not x_cemab_event_token or x_cemab_event_token != segredo:
        raise HTTPException(status_code=401, detail="Credencial do webhook inválida.")


def _data_hora_local(valor) -> datetime:
    """Aceita data ISO-8601 ou timestamp Unix — NÃO duplica deslocamento!"""
    if isinstance(valor, datetime):
        dt = valor
    elif isinstance(valor, (int, float)):
        timestamp = float(valor)
        if abs(timestamp) > 100_000_000_000:
            timestamp /= 1000.0
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    else:
        texto = str(valor).strip()
        if not texto:
            raise ValueError("data_hora não pode ser vazia")
        if re.fullmatch(r"\d{10,13}(?:\.\d+)?", texto):
            timestamp = float(texto)
            if abs(timestamp) > 100_000_000_000:
                timestamp /= 1000.0
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        else:
            dt = datetime.fromisoformat(texto.replace("Z", "+00:00"))
            # ✅ SÓ atribui fuso se REALMENTE não tiver offset
            if dt.tzinfo is None or dt.utcoffset() is None:
                dt = dt.replace(tzinfo=_BRASILIA)
    # ✅ Converte UMA vez só para o fuso de Brasilia/Teresina
    return dt.astimezone(_BRASILIA)

def _texto(valor, limite=160):
    if valor is None:
        return None
    resultado = str(valor).strip()
    return resultado[:limite] if resultado else None


def _external_id(dados: EventoPresencaRequest, matricula: str, dt: datetime) -> str:
    origem = _texto(dados.id_evento, 110) or _texto(dados.id_log, 110)
    if origem:
        # Mantém o prefixo dentro do limite de 120 caracteres da coluna.
        return ("controlid:" + origem)[:120]
    identificador = "|".join([
        matricula, dt.isoformat(), _texto(dados.identificacao, 80) or "",
        _texto(dados.codigo_usuario, 80) or "",
    ])
    return "sha256:" + hashlib.sha256(identificador.encode("utf-8")).hexdigest()


def _mensagem_presenca(nome: str, dt: datetime) -> tuple[str, str]:
    hora = dt.strftime("%H:%M")
    return "Presença registrada na escola", f"{nome} passou pelo reconhecimento facial às {hora}."


def _enviar_push(token: str, dados: dict, titulo: str, mensagem_texto: str):
    payload_data = {k: str(v) for k, v in dados.items() if v is not None}
    mensagem = messaging.Message(
        notification=messaging.Notification(title=titulo, body=mensagem_texto),
        data=payload_data,
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(sound="default", color="#176B52"),
        ),
        token=token,
    )
    return messaging.send(mensagem)


def _remover_token_fcm_invalido(session: Session, token: str) -> None:
    """Limpa associações antigas quando o FCM confirma que um token não existe mais."""
    dispositivo = session.exec(select(UserM).where(UserM.token == token)).first()
    if not dispositivo:
        return
    vinculos = session.exec(
        select(AlunoDispositivo).where(AlunoDispositivo.user_id == dispositivo.id)
    ).all()
    for vinculo in vinculos:
        session.delete(vinculo)
    # Remove as chaves estrangeiras antes do registro do dispositivo.
    session.flush()
    session.delete(dispositivo)


def _processar_evento(dados: EventoPresencaRequest) -> dict:
    matricula = normalizar_matricula(dados.matricula)
    if not matricula or len(matricula) > 40:
        return {"success": False, "status": "matricula_invalida", "matricula": str(dados.matricula)[:40]}
    try:
        dt = _data_hora_local(dados.data_hora)
    except (ValueError, TypeError, OverflowError, OSError) as exc:
        return {"success": False, "status": "data_hora_invalida", "matricula": matricula, "detail": str(exc)}

    external_id = _external_id(dados, matricula, dt)
    data_iso = dt.isoformat()
    identificacao = _texto(dados.identificacao, 80)
    codigo_usuario = _texto(dados.codigo_usuario, 80)
    autorizacao = _texto(dados.autorizacao, 80)

    with Session(get_engine()) as session:
        existente = session.exec(select(EventoPresenca).where(EventoPresenca.external_id == external_id)).first()
        if existente and existente.envio_status in {"enviado", "parcial"}:
            return {
                "success": existente.envio_status in {"enviado", "parcial"},
                "duplicado": True,
                "evento_id": existente.external_id,
                "status": existente.envio_status,
                "tokens_enviados": existente.tokens_enviados,
            }

        aluno = localizar_aluno_por_matricula(session, matricula)
        nome_evento = _texto(dados.nome_completo, 160)
        nome_oficial = aluno.nome_completo if aluno else (nome_evento or "Aluno não identificado")

        if existente:
            evento = existente
            evento.matricula = matricula
            evento.nome_completo = nome_oficial
            evento.data_hora = data_iso
            evento.identificacao = identificacao
            evento.codigo_usuario = codigo_usuario
            evento.autorizacao = autorizacao
            evento.aluno_id = aluno.id if aluno else None
            evento.envio_status = "pendente"
            evento.tokens_enviados = 0
        else:
            evento = EventoPresenca(
                external_id=external_id,
                aluno_id=aluno.id if aluno else None,
                matricula=matricula,
                nome_completo=nome_oficial,
                data_hora=data_iso,
                identificacao=identificacao,
                codigo_usuario=codigo_usuario,
                autorizacao=autorizacao,
                envio_status="pendente",
                tokens_enviados=0,
            )
            session.add(evento)
        session.commit()
        session.refresh(evento)

        if not aluno or not aluno.ativo:
            evento.envio_status = "aluno_nao_cadastrado"
            session.add(evento)
            session.commit()
            return {"success": False, "evento_id": external_id, "matricula": matricula, "status": "aluno_nao_cadastrado", "detail": "A matrícula não consta no cadastro de alunos ativos."}

        links = session.exec(select(AlunoDispositivo).where(AlunoDispositivo.aluno_id == aluno.id)).all()
        tokens = []
        for link in links:
            user = session.get(UserM, link.user_id)
            if user and user.token and user.token not in tokens:
                tokens.append(user.token)

        if not tokens:
            evento.envio_status = "sem_vinculo"
            session.add(evento)
            session.commit()
            return {"success": True, "evento_id": external_id, "matricula": matricula, "status": "sem_vinculo", "tokens_destino": 0, "tokens_enviados": 0}

        try:
            ensure_firebase_app()
        except Exception as exc:
            evento.envio_status = "erro_firebase"
            session.add(evento)
            session.commit()
            # Não retornar detalhes internos de credenciais Firebase ao chamador.
            raise HTTPException(status_code=503, detail="O serviço de notificações Firebase não está configurado corretamente no servidor.") from exc

        titulo, mensagem_texto = _mensagem_presenca(aluno.nome_completo, dt)
        data_payload = {
            "tipo": "presenca",
            "evento_id": external_id,
            "open_notification": "1",
            "matricula": aluno.matricula,
            "nome_completo": aluno.nome_completo,
            "data_hora": data_iso,
            "hora_aproximada": dt.strftime("%H:%M"),
            "titulo": titulo,
            "mensagem": mensagem_texto,
            "identificacao": identificacao or "",
            "codigo_usuario": codigo_usuario or "",
            "autorizacao": autorizacao or "",
        }
        enviados = 0
        erros = []
        for token in tokens:
            try:
                _enviar_push(token, data_payload, titulo, mensagem_texto)
                enviados += 1
            except Exception as exc:  # Um dispositivo com token inválido não impede os demais.
                erro_tipo = type(exc).__name__
                # O token pode ter sido invalidado após a desinstalação do aplicativo.
                # Remove somente quando o SDK informa explicitamente que não está registrado.
                if erro_tipo == "UnregisteredError":
                    _remover_token_fcm_invalido(session, token)
                # Não devolve mensagens completas do SDK, que podem conter detalhes do token.
                erros.append(erro_tipo)

        evento.tokens_enviados = enviados
        if enviados == len(tokens):
            evento.envio_status = "enviado"
        elif enviados > 0:
            evento.envio_status = "parcial"
        else:
            evento.envio_status = "erro"
        session.add(evento)
        session.commit()

        return {
            "success": enviados > 0,
            "evento_id": external_id,
            "matricula": aluno.matricula,
            "status": evento.envio_status,
            "tokens_destino": len(tokens),
            "tokens_enviados": enviados,
            "erros": erros,
        }


@router.post("/evento", status_code=status.HTTP_200_OK, dependencies=[Depends(validar_token_eventos)])
def receber_evento(dados: EventoPresencaRequest):
    """Recebe uma presença processada e notifica os dispositivos do aluno."""
    return _processar_evento(dados)


@router.post("/eventos", status_code=status.HTTP_200_OK, dependencies=[Depends(validar_token_eventos)])
def receber_lote(dados: EventoPresencaLoteRequest):
    """Recebe um lote de presenças já processadas pela automação externa."""
    resultados = []
    for evento in dados.eventos:
        try:
            resultados.append(_processar_evento(evento))
        except HTTPException as exc:
            resultados.append({"success": False, "status": "erro", "matricula": evento.matricula, "detail": exc.detail})
    return {
        "success": all(item.get("success", False) or item.get("status") in {"sem_vinculo", "duplicado"} for item in resultados),
        "total_recebido": len(dados.eventos),
        "notificados": sum(1 for item in resultados if item.get("status") in {"enviado", "parcial"}),
        "resultados": resultados,
    }


@router.get("/historico", status_code=status.HTTP_200_OK)
def historico_notificacoes(token: str | None = Header(default=None, alias="X-FCM-Token", min_length=10, max_length=4096), limite: int = Query(default=100, ge=1, le=300)):
    """Histórico de eventos enviados aos alunos vinculados a este dispositivo."""
    if not token:
        raise HTTPException(status_code=401, detail="Token FCM obrigatório para consultar o histórico.")
    with Session(get_engine()) as session:
        user = session.exec(select(UserM).where(UserM.token == token.strip())).first()
        if not user:
            return {"success": True, "notificacoes": []}
        links = session.exec(select(AlunoDispositivo).where(AlunoDispositivo.user_id == user.id)).all()
        aluno_ids = [link.aluno_id for link in links]
        if not aluno_ids:
            return {"success": True, "notificacoes": []}

        eventos = session.exec(
            select(EventoPresenca)
            .where(EventoPresenca.aluno_id.in_(aluno_ids))
            .where(EventoPresenca.envio_status.in_(["enviado", "parcial"]))
            .order_by(EventoPresenca.criado_em.desc())
            .limit(limite)
        ).all()
        notificacoes = []
        for evento in eventos:
            try:
                dt = _data_hora_local(evento.data_hora)
                hora = dt.strftime("%H:%M")
                titulo, corpo = _mensagem_presenca(evento.nome_completo, dt)
            except (ValueError, TypeError, OverflowError, OSError):
                hora = "Não informado"
                titulo = "Presença registrada na escola"
                corpo = f"{evento.nome_completo} teve um registro de presença na escola."
            recebida_em = evento.criado_em
            # SQLite pode devolver datetimes sem tzinfo embora tenham sido criados em UTC.
            if recebida_em.tzinfo is None:
                recebida_em = recebida_em.replace(tzinfo=timezone.utc)
            else:
                recebida_em = recebida_em.astimezone(timezone.utc)
            notificacoes.append({
                "evento_id": evento.external_id,
                "tipo": "presenca",
                "titulo": titulo,
                "mensagem": corpo,
                "matricula": evento.matricula,
                "nome_completo": evento.nome_completo,
                "data_hora": evento.data_hora,
                "hora_aproximada": hora,
                "recebida_em": recebida_em.isoformat(),
                "lida": False,
            })
        return {"success": True, "notificacoes": notificacoes}
