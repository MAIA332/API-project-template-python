import asyncio
import sys
from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn
from motor.motor_asyncio import AsyncIOMotorClient

# Importações internas seguindo a Tree do projeto
from database.prisma.prisma import prisma_connection
from bootstrap.bootstrap_app import BootstrapApp
from servers.ws_server import WebSocketServer

# Variáveis globais para controle de ciclo de vida
ws_task: asyncio.Task | None = None
mongo_client: AsyncIOMotorClient | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global ws_task, mongo_client
    
    print("🚀 [LIFESPAN] Iniciando ciclo de vida da aplicação...")

    # 1. Inicializar Conexões de Banco de Dados
    # Postgres (Prisma)
    await prisma_connection.connect()
    
    # MongoDB (Motor) - Ajuste a URL conforme seu docker-compose.yml
    mongo_client = AsyncIOMotorClient("mongodb://localhost:27017")
    
    # 2. Inicializar Servidor WebSocket
    ws_server = WebSocketServer()
    ws_task = asyncio.create_task(ws_server.start())
    print("🌐 [WS] Servidor WebSocket iniciado em background")

    # 3. Executar o Bootstrap do Sistema
    # Injeta Prisma, Mongo e WS Server para criar Services -> Controllers -> Routers
    bootstrap = BootstrapApp(
        prisma_client=prisma_connection.prisma,
        mongodb_client=mongo_client,
        ws_server=ws_server
    )
    
    # O bootstrap agora recebe a instância do 'app' para registrar as rotas dinamicamente
    await bootstrap.bootstrap(app)

    # 4. Guardar instâncias no estado do app para acesso via dependência se necessário
    app.state.services = bootstrap.services
    app.state.controllers = bootstrap.controllers

    yield  # --- Aplicação rodando ---

    # 5. Shutdown: Encerrar tudo corretamente
    print("🛑 [SHUTDOWN] Encerrando serviços...")
    
    if ws_task:
        ws_task.cancel()
        try:
            await ws_task
        except asyncio.CancelledError:
            print("✅ [WS] Task finalizada")

    await prisma_connection.disconnect()
    mongo_client.close()
    print("✅ [DB] Conexões de banco de dados encerradas")


# Inicialização do FastAPI com o Lifespan configurado
app = FastAPI(
    title="Sinapse Labs - Cortex API",
    lifespan=lifespan
)

def run():
    """
    Configuração de execução para suportar Windows (necessário para o seu ambiente local)
    e o loop de eventos assíncronos do Uvicorn.
    """
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    config = uvicorn.Config(
        app="server:app", # Importação em string para suportar reload se desejar
        host="0.0.0.0", 
        port=8000, 
        log_level="info",
        reload=True # Útil para o desenvolvimento do time (Felipe, Henrique, etc)
    )
    server = uvicorn.Server(config)
    asyncio.run(server.serve())

if __name__ == "__main__":
    run()