from fastapi import APIRouter, status

router = APIRouter()

# Lista os verbos disponiveis para essecontroller

@router.options("/", status_code=status.HTTP_200_OK)
async def options_emails():
    return { "methods": ["GET"] }

@router.get("/", status_code=status.HTTP_200_OK)
def index():
    return {"Documentação": "Acesse: https://github.com/davidsousadev/apisme"}