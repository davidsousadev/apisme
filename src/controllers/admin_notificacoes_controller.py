# -*- coding: utf-8 -*-
"""Área administrativa para faltas e notificações personalizadas do CEMAB."""
from datetime import date, datetime, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from decouple import config
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from firebase_admin import messaging

from src.database import get_engine
from src.firebase_service import ensure_firebase_app
from src.models.aluno_models import Aluno, AlunoDispositivo, EventoPresenca, NotificacaoAdministrativa
from src.models.users_models import UserM
from src.controllers.alunos_controller import normalizar_matricula, localizar_aluno_por_matricula

router = APIRouter()
FUSO = ZoneInfo("America/Fortaleza")


def validar_admin(x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")):
    segredo = config("ALUNOS_ADMIN_TOKEN", default="").strip()
    if not segredo:
        raise HTTPException(status_code=503, detail="Configure ALUNOS_ADMIN_TOKEN nas variáveis de ambiente da API.")
    if not x_admin_token or x_admin_token != segredo:
        raise HTTPException(status_code=401, detail="Token administrativo inválido.")


class EnviarFaltasRequest(BaseModel):
    data: date
    titulo: str = Field(default="Falta registrada", min_length=3, max_length=120)
    mensagem: str = Field(default="Não identificamos a passagem do aluno pelo leitor facial nesta data. Em caso de divergência, entre em contato com a escola.", min_length=5, max_length=1000)


class PersonalizadaRequest(BaseModel):
    titulo: str = Field(min_length=3, max_length=120)
    mensagem: str = Field(min_length=2, max_length=1000)
    destino: str = Field(default="todos", pattern="^(todos|aluno)$")
    matricula: str | None = Field(default=None, max_length=40)


def _tokens_aluno(session: Session, aluno_id: int) -> list[str]:
    links = session.exec(select(AlunoDispositivo).where(AlunoDispositivo.aluno_id == aluno_id)).all()
    tokens = []
    for link in links:
        user = session.get(UserM, link.user_id)
        if user and user.token and user.token not in tokens:
            tokens.append(user.token)
    return tokens


def _enviar(token: str, payload: dict, titulo: str, mensagem: str) -> bool:
    data = {str(k): str(v) for k, v in payload.items() if v is not None}
    msg = messaging.Message(
        notification=messaging.Notification(title=titulo, body=mensagem),
        data=data,
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(sound="default", color="#176B52"),
        ),
        token=token,
    )
    messaging.send(msg)
    return True


def _presente_na_data(evento: EventoPresenca, dia: date) -> bool:
    try:
        dt = datetime.fromisoformat(str(evento.data_hora).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(FUSO).date() == dia
    except (ValueError, TypeError, OverflowError):
        return False


def _salvar_notificacao(session, external_id, tipo, titulo, mensagem, aluno, dia, enviados):
    item = NotificacaoAdministrativa(
        external_id=external_id, tipo=tipo, titulo=titulo, mensagem=mensagem,
        aluno_id=aluno.id if aluno else None,
        matricula=aluno.matricula if aluno else None,
        nome_completo=aluno.nome_completo if aluno else None,
        data_referencia=dia.isoformat() if dia else None,
        tokens_enviados=enviados,
    )
    session.add(item)


@router.get("", response_class=HTMLResponse)
def painel_admin():
    return HTMLResponse(ADMIN_HTML)


@router.get("/api/alunos", dependencies=[Depends(validar_admin)])
def listar_alunos():
    with Session(get_engine()) as session:
        alunos = session.exec(select(Aluno).where(Aluno.ativo == True).order_by(Aluno.nome_completo)).all()  # noqa: E712
        return {"success": True, "alunos": [{"matricula": a.matricula, "nome_completo": a.nome_completo} for a in alunos]}


@router.get("/api/resumo", dependencies=[Depends(validar_admin)])
def resumo(data: date = Query(default_factory=lambda: datetime.now(FUSO).date())):
    with Session(get_engine()) as session:
        alunos = session.exec(select(Aluno).where(Aluno.ativo == True)).all()  # noqa: E712
        eventos = session.exec(select(EventoPresenca)).all()
        presentes = {e.aluno_id for e in eventos if e.aluno_id and _presente_na_data(e, data)}
        enviados = session.exec(select(NotificacaoAdministrativa).where(NotificacaoAdministrativa.tipo == "falta").where(NotificacaoAdministrativa.data_referencia == data.isoformat())).all()
        return {"success": True, "data": data.isoformat(), "alunos_ativos": len(alunos), "presentes": len(presentes), "faltas_calculadas": sum(1 for a in alunos if a.id not in presentes), "faltas_ja_notificadas": len({n.aluno_id for n in enviados if n.aluno_id})}


@router.post("/api/faltas/enviar", dependencies=[Depends(validar_admin)])
def enviar_faltas(dados: EnviarFaltasRequest):
    with Session(get_engine()) as session:
        alunos = session.exec(select(Aluno).where(Aluno.ativo == True).order_by(Aluno.nome_completo)).all()  # noqa: E712
        eventos = session.exec(select(EventoPresenca)).all()
        presentes = {e.aluno_id for e in eventos if e.aluno_id and _presente_na_data(e, dados.data)}
        ja_enviadas = session.exec(select(NotificacaoAdministrativa).where(NotificacaoAdministrativa.tipo == "falta").where(NotificacaoAdministrativa.data_referencia == dados.data.isoformat())).all()
        notificados = {n.aluno_id for n in ja_enviadas if n.aluno_id}
        ausentes = [a for a in alunos if a.id not in presentes and a.id not in notificados]
        if not ausentes:
            return {"success": True, "data": dados.data.isoformat(), "faltas_identificadas": sum(1 for a in alunos if a.id not in presentes), "notificacoes_enviadas": 0, "sem_vinculo": 0, "ja_notificados": len(notificados), "message": "Não há novas faltas para notificar nesta data."}
        try:
            ensure_firebase_app()
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Firebase não está configurado corretamente na API.") from exc
        total_enviados = sem_vinculo = 0
        resultados = []
        for aluno in ausentes:
            tokens = _tokens_aluno(session, aluno.id)
            enviados = 0
            for token in tokens:
                try:
                    _enviar(token, {"tipo":"falta", "evento_id":f"falta:{dados.data.isoformat()}:{aluno.id}", "open_notification":"1", "matricula":aluno.matricula, "nome_completo":aluno.nome_completo, "titulo":dados.titulo, "mensagem":dados.mensagem, "data_referencia":dados.data.isoformat()}, dados.titulo, f"{aluno.nome_completo}: {dados.mensagem}")
                    enviados += 1
                except Exception:
                    pass
            if not tokens:
                sem_vinculo += 1
            if enviados:
                total_enviados += enviados
                _salvar_notificacao(session, f"falta:{dados.data.isoformat()}:{aluno.id}", "falta", dados.titulo, dados.mensagem, aluno, dados.data, enviados)
            resultados.append({"matricula":aluno.matricula,"nome_completo":aluno.nome_completo,"tokens_enviados":enviados,"status":"enviado" if enviados else ("sem_vinculo" if not tokens else "erro_envio")})
        session.commit()
        return {"success": True, "data": dados.data.isoformat(), "faltas_identificadas": sum(1 for a in alunos if a.id not in presentes), "notificacoes_enviadas": total_enviados, "alunos_notificados": sum(1 for r in resultados if r["tokens_enviados"]), "sem_vinculo": sem_vinculo, "ja_notificados": len(notificados), "resultados": resultados}


@router.post("/api/personalizada/enviar", dependencies=[Depends(validar_admin)])
def enviar_personalizada(dados: PersonalizadaRequest):
    with Session(get_engine()) as session:
        if dados.destino == "aluno":
            if not dados.matricula:
                raise HTTPException(status_code=422, detail="Informe a matrícula do aluno.")
            aluno = localizar_aluno_por_matricula(session, normalizar_matricula(dados.matricula))
            if not aluno or not aluno.ativo:
                raise HTTPException(status_code=404, detail="Aluno ativo não encontrado para essa matrícula.")
            alunos = [aluno]
        else:
            alunos = session.exec(select(Aluno).where(Aluno.ativo == True).order_by(Aluno.nome_completo)).all()  # noqa: E712
        try:
            ensure_firebase_app()
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Firebase não está configurado corretamente na API.") from exc
        total = sem_vinculo = alunos_notificados = 0
        falhas = []
        for aluno in alunos:
            tokens = _tokens_aluno(session, aluno.id)
            enviados = 0
            external_id = f"aviso:{uuid4().hex}"
            for token in tokens:
                try:
                    _enviar(token, {"tipo":"aviso", "evento_id":external_id, "open_notification":"1", "matricula":aluno.matricula, "nome_completo":aluno.nome_completo, "titulo":dados.titulo, "mensagem":dados.mensagem}, dados.titulo, dados.mensagem)
                    enviados += 1
                except Exception:
                    pass
            if not tokens:
                sem_vinculo += 1
            if enviados:
                total += enviados; alunos_notificados += 1
                _salvar_notificacao(session, external_id, "aviso", dados.titulo, dados.mensagem, aluno, None, enviados)
            else:
                falhas.append({"matricula":aluno.matricula,"nome_completo":aluno.nome_completo,"status":"sem_vinculo" if not tokens else "erro_envio"})
        session.commit()
        return {"success": True, "destino": dados.destino, "alunos_alvo": len(alunos), "alunos_notificados": alunos_notificados, "notificacoes_enviadas": total, "sem_vinculo": sem_vinculo, "falhas": falhas}


@router.get("/api/historico", dependencies=[Depends(validar_admin)])
def historico_admin(limite: int = Query(default=100, ge=1, le=500)):
    with Session(get_engine()) as session:
        rows = session.exec(select(NotificacaoAdministrativa).order_by(NotificacaoAdministrativa.criado_em.desc()).limit(limite)).all()
        return {"success": True, "notificacoes": [{"tipo":r.tipo,"titulo":r.titulo,"mensagem":r.mensagem,"matricula":r.matricula,"nome_completo":r.nome_completo,"data_referencia":r.data_referencia,"tokens_enviados":r.tokens_enviados,"criado_em":r.criado_em.isoformat()} for r in rows]}


ADMIN_HTML = r'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CEMAB | Notificações</title><style>
:root{font-family:Inter,system-ui,Arial,sans-serif;color:#17231f;background:#f3f6f5}*{box-sizing:border-box}body{margin:0}.top{background:#145b48;color:white;padding:24px max(20px,calc((100% - 1100px)/2))}.top h1{margin:0 0 5px;font-size:25px}.top p{margin:0;opacity:.85}.wrap{max-width:1100px;margin:24px auto;padding:0 16px}.card{background:white;border:1px solid #dce5e1;border-radius:14px;padding:20px;margin-bottom:18px;box-shadow:0 3px 14px #173e3010}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}.stat{background:#f4f8f6;border-radius:10px;padding:14px}.stat strong{font-size:25px;display:block}.stat span{font-size:13px;color:#52665e}label{display:block;font-size:14px;font-weight:650;margin:12px 0 6px}input,select,textarea{width:100%;border:1px solid #cbd8d2;border-radius:8px;padding:11px;font:inherit;background:white}textarea{min-height:95px;resize:vertical}button{border:0;border-radius:8px;padding:11px 16px;background:#176b52;color:white;font-weight:700;cursor:pointer;margin-top:12px}button.secondary{background:#e6efeb;color:#174e3f}button:disabled{opacity:.55}.muted{color:#60736b;font-size:13px}.msg{padding:12px;border-radius:8px;background:#eef6f1;margin-top:12px;white-space:pre-wrap}.err{background:#fff0ee;color:#8a281e}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:10px;border-bottom:1px solid #e4ebe7;font-size:14px}th{color:#53675e}@media(max-width:600px){.card{padding:15px;overflow-x:auto}}
</style></head><body><header class="top"><h1>🏫 CEMAB · Central de notificações</h1><p>Envio de avisos aos responsáveis vinculados aos alunos</p></header><main class="wrap"><section class="card" id="login"><h2>Acesso administrativo</h2><p class="muted">Informe o token configurado na variável ALUNOS_ADMIN_TOKEN da API. Ele fica somente nesta sessão do navegador.</p><label for="token">Token administrativo</label><input id="token" type="password" autocomplete="current-password"><button id="connect">Entrar</button><div id="loginMsg" class="msg" hidden></div></section><div id="panel" hidden><section class="card"><h2>Resumo das faltas</h2><div class="grid"><div><label for="dia">Data de referência</label><input id="dia" type="date"></div><div style="align-self:end"><button id="refresh" class="secondary">Atualizar resumo</button></div></div><div class="stats" id="stats"></div><p class="muted">IMPORTANTE: antes de enviar, importe o relatório Control iD completo e confirme que o envio à API terminou. Se as passagens ainda não chegaram, alunos presentes podem ser classificados como faltosos. A falta é calculada comparando o cadastro com as passagens recebidas para a data escolhida.</p></section><section class="card"><h2>Enviar notificações de falta</h2><p>Notifica os responsáveis vinculados aos alunos ativos sem registro de passagem na data selecionada. Para evitar duplicidade, cada aluno recebe no máximo um envio de falta por data.</p><label for="ftitulo">Título</label><input id="ftitulo" maxlength="120" value="Falta registrada"><label for="fmsg">Mensagem</label><textarea id="fmsg">Não identificamos a passagem do aluno pelo leitor facial nesta data. Em caso de divergência, entre em contato com a escola.</textarea><button id="sendAbs">Calcular e enviar faltas</button><div id="absMsg" class="msg" hidden></div></section><section class="card"><h2>Notificação personalizada</h2><label for="destino">Destinatários</label><select id="destino"><option value="todos">Todos os alunos ativos com dispositivo vinculado</option><option value="aluno">Um aluno específico</option></select><div id="studentBox" hidden><label for="matricula">Aluno</label><select id="matricula"><option value="">Selecione um aluno</option></select></div><label for="ptitulo">Título</label><input id="ptitulo" maxlength="120" placeholder="Ex.: Reunião de responsáveis"><label for="pmsg">Mensagem</label><textarea id="pmsg" maxlength="1000" placeholder="Digite o aviso que será enviado..."></textarea><button id="sendCustom">Enviar notificação</button><div id="customMsg" class="msg" hidden></div></section><section class="card"><h2>Histórico de envios</h2><button id="historyBtn" class="secondary">Atualizar histórico</button><div id="history" class="muted" style="margin-top:12px">Nenhum dado carregado.</div></section></div></main><script>
const $=id=>document.getElementById(id);let adminToken='',students=[];const today=new Date();$('dia').value=new Date(today.getTime()-today.getTimezoneOffset()*60000).toISOString().slice(0,10);
function msg(id,text,err=false){const e=$(id);e.hidden=false;e.textContent=text;e.className='msg'+(err?' err':'')}
async function api(path,method='GET',body){const r=await fetch('/admin/api'+path,{method,headers:{'X-Admin-Token':adminToken,'Content-Type':'application/json','Accept':'application/json'},body:body?JSON.stringify(body):undefined});let d={};try{d=await r.json()}catch{}if(!r.ok)throw Error(d.detail||'Erro HTTP '+r.status);return d}
$('connect').onclick=async()=>{adminToken=$('token').value.trim();try{const d=await api('/alunos');students=d.alunos;$('matricula').innerHTML='<option value="">Selecione um aluno</option>'+students.map(a=>`<option value="${a.matricula}">${a.nome_completo} — ${a.matricula}</option>`).join('');$('login').hidden=true;$('panel').hidden=false;await refresh();await history()}catch(e){msg('loginMsg',e.message,true)}};
async function refresh(){const d=await api('/resumo?data='+encodeURIComponent($('dia').value));$('stats').innerHTML=[['Alunos ativos',d.alunos_ativos],['Presentes registrados',d.presentes],['Faltas calculadas',d.faltas_calculadas],['Já notificados',d.faltas_ja_notificadas]].map(x=>`<div class="stat"><strong>${x[1]}</strong><span>${x[0]}</span></div>`).join('')}
$('refresh').onclick=async()=>{try{await refresh()}catch(e){msg('absMsg',e.message,true)}};
$('sendAbs').onclick=async()=>{if(!confirm('Enviar notificações de falta para os alunos sem passagem em '+$('dia').value+'?'))return;const b=$('sendAbs');b.disabled=true;try{const d=await api('/faltas/enviar','POST',{data:$('dia').value,titulo:$('ftitulo').value,mensagem:$('fmsg').value});msg('absMsg',`Faltas identificadas: ${d.faltas_identificadas}\nAlunos notificados: ${d.alunos_notificados||0}\nNotificações enviadas aos dispositivos: ${d.notificacoes_enviadas}\nSem dispositivo vinculado: ${d.sem_vinculo}\nJá notificados anteriormente: ${d.ja_notificados}`);await refresh();await history()}catch(e){msg('absMsg',e.message,true)}finally{b.disabled=false}};
$('destino').onchange=()=>{$('studentBox').hidden=$('destino').value!=='aluno'};
$('sendCustom').onclick=async()=>{const titulo=$('ptitulo').value.trim(),mensagem=$('pmsg').value.trim();if(!titulo||!mensagem){msg('customMsg','Preencha o título e a mensagem.',true);return}if($('destino').value==='aluno'&&!$('matricula').value){msg('customMsg','Selecione o aluno.',true);return}if(!confirm('Confirma o envio desta notificação?'))return;const b=$('sendCustom');b.disabled=true;try{const d=await api('/personalizada/enviar','POST',{titulo,mensagem,destino:$('destino').value,matricula:$('destino').value==='aluno'?$('matricula').value:null});msg('customMsg',`Alunos notificados: ${d.alunos_notificados}\nNotificações enviadas: ${d.notificacoes_enviadas}\nSem vínculo: ${d.sem_vinculo}`);await history()}catch(e){msg('customMsg',e.message,true)}finally{b.disabled=false}};
async function history(){const d=await api('/historico?limite=100');if(!d.notificacoes.length){$('history').textContent='Nenhuma notificação enviada ainda.';return}$('history').innerHTML='<table><thead><tr><th>Data</th><th>Tipo</th><th>Aluno</th><th>Título</th><th>Dispositivos</th></tr></thead><tbody>'+d.notificacoes.map(n=>`<tr><td>${new Date(n.criado_em).toLocaleString('pt-BR')}</td><td>${n.tipo}</td><td>${n.nome_completo||'Todos'}<br><small>${n.matricula||''}</small></td><td>${n.titulo}<br><small>${n.mensagem}</small></td><td>${n.tokens_enviados}</td></tr>`).join('')+'</tbody></table>'}
$('historyBtn').onclick=()=>history().catch(e=>msg('customMsg',e.message,true));
</script></body></html>'''
