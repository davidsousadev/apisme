from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Importação de todos controladores
from .controllers.index_controller import router as index_router
from .controllers.users_controller import router as user_router
from .controllers.firebase_controller import router as firebase_router
from .controllers.testeme_controller import router as testeme_router

from .database import init_db

def create_app():

    # Inicializa a aplicação
    app = FastAPI(
        title="APIS ME",
        description="API para gerenciar todas as operações de testes de sistemas",
        version="1.0.0",
    )

    # Configuração de CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # ! Restringir em produção
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Middleware TrustedHost sem parâmetros incorretos
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=["*"],  # ! Restringir em produção
    )  

    # Registro das rotas
    # /
    app.include_router(index_router, prefix="", tags=["root"])
    app.include_router(user_router, prefix="/users", tags=["Users"])
    app.include_router(firebase_router, prefix="/fire", tags=["Firebase"])
    app.include_router(testeme_router, prefix="/testeme", tags=["Teste Me - Seu desafio diário"])
    # Inicialização do banco de dados
    init_db()

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    import os

    # Porta dinâmica para compatibilidade com serviços do Vercel
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("src.main:app", host="0.0.0.0", port=port, reload=True)
    
