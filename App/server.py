import asyncio
import sys
from fastapi import FastAPI, WebSocket
from contextlib import asynccontextmanager
import uvicorn

from database.prisma.prisma import prisma_connection
from database.mongo.mongodb import mongo_connection 

from bootstrap.bootstrap_app import BootstrapApp
from servers.ws_server import WebSocketServer

from API.middlewares.auth.authentication import AuthenticationMiddleware
from API.middlewares.auth.check_roles import check_roles
from fastapi.middleware import Middleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 [LIFESPAN] Iniciando ciclo de vida da aplicação...")

    # 1. Inicializar Conexões de Banco de Dados
    await prisma_connection.connect()
    await mongo_connection.connect()
    
    # 2. Inicializar Servidor WebSocket (Agora sem asyncio.create_task)
    ws_server = WebSocketServer()
    print("🌐 [WS] Instância do WebSocketServer criada e pronta para o FastAPI")

    # 3. Executar o Bootstrap do Sistema
    bootstrap = BootstrapApp(
        prisma_client=prisma_connection.prisma,
        mongodb_client=mongo_connection.client,
        ws_server=ws_server
    )
    
    await bootstrap.bootstrap(app)

    # 4. Guardar instâncias no estado do app
    app.state.services = bootstrap.services
    app.state.controllers = bootstrap.controllers
    app.state.pipelines = bootstrap.pipelines
    app.state.prisma = prisma_connection.prisma
    app.state.ws_server = ws_server  # Salvando para usar na rota raiz de WS

    yield  # --- Aplicação rodando ---

    # 5. Shutdown: Encerrar tudo corretamente
    print("🛑 [SHUTDOWN] Encerrando serviços...")
    await prisma_connection.disconnect()
    mongo_connection.disconnect()
    print("✅ [DB] Conexões de banco de dados encerradas")


# ATENÇÃO AOS MIDDLEWARES: 
# Se o seu AuthenticationMiddleware der block em rotas que não tem cabeçalho "Bearer Token", 
# e a conexão WebSocket for barrada (Erro 403), você precisará adicionar uma exceção
# no código do middleware para ignorar a rota "/ws".
middlewares = [
    Middleware(AuthenticationMiddleware, prisma=prisma_connection.prisma),
]

# Inicialização do FastAPI com o Lifespan configurado
app = FastAPI(
    title="Sinapse Labs - Cortex API",
    lifespan=lifespan,
    middleware=middlewares
)

# ================= ROTA WEBSOCKET NATIVA =================
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Repassa a conexão para a sua classe que já controla as salas e eventos
    await app.state.ws_server.handler(websocket)
# =========================================================

def run():
    """
    Configuração de execução para suportar Windows
    e o loop de eventos assíncronos do Uvicorn.
    """
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    config = uvicorn.Config(
        app="server:app", 
        host="0.0.0.0", 
        port=8000, 
        log_level="info",
        reload=True 
    )
    server = uvicorn.Server(config)
    asyncio.run(server.serve())

if __name__ == "__main__":
    run()