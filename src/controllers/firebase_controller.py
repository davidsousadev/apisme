from decouple import config
import firebase_admin
from firebase_admin import credentials, messaging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from src.database import get_engine  # ajuste para o caminho real
from src.models.users_models import User, UserResponse  # ajuste para o caminho real

# Configuração Firebase com decouple
firebase_config = {
    "type": config("FIREBASE_TYPE"),
    "project_id": config("FIREBASE_PROJECT_ID"),
    "private_key_id": config("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": config("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),
    "client_email": config("FIREBASE_CLIENT_EMAIL"),
    "client_id": config("FIREBASE_CLIENT_ID"),
    "auth_uri": config("FIREBASE_AUTH_URI"),
    "token_uri": config("FIREBASE_TOKEN_URI"),
    "auth_provider_x509_cert_url": config("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": config("FIREBASE_CLIENT_X509_CERT_URL"),
    "universe_domain": config("FIREBASE_UNIVERSE_DOMAIN"),
}

# Inicializa Firebase apenas uma vez
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred)

router = APIRouter()

@router.get("/send/{user_id}/{id_mensagem}")
def send_notification(user_id: int, id_mensagem: int):
    with Session(get_engine()) as session:
        user = session.exec(select(User).where(User.id == user_id)).first()

        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")

        registration_token = user.token

        # Mensagem com id_mensagem vindo da URL
        message = messaging.Message(
            notification=messaging.Notification(
                title="Promoção Exclusiva 🚀",
                body=f"Produto em promoção! ID {id_mensagem}"
            ),
            data={
                "tipo": "promocao",
                "id_mensagem": str(id_mensagem)
            },
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default",
                    color="#0000FF",
                    channel_id="mensagens_importantes",
                    click_action="CHAT_ACTIVITY"
                )
            ),
            token=registration_token,
        )

        try:
            response = messaging.send(message)
            return {"success": True, "response": response}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao enviar notificação: {str(e)}")