import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

class MongoDBConnection:
    def __init__(self):
        # Busca a URL do .env ou usa o padrão do Docker
        self.uri = os.getenv("MONGO_URL", "mongodb://localhost:27017")
        self.db_name = os.getenv("MONGO_DB_NAME", "cortex_logs")
        self.client: AsyncIOMotorClient = None
        self.db = None

    async def connect(self):
        """Inicializa a conexão com o MongoDB"""
        if not self.client:
            print(f"🍃 [MONGO] Conectando ao banco: {self.db_name}")
            self.client = AsyncIOMotorClient(self.uri)
            self.db = self.client[self.db_name]
            print("✅ [MONGO] Conexão estabelecida")

    def disconnect(self):
        """Fecha a conexão"""
        if self.client:
            self.client.close()
            print("🛑 [MONGO] Conexão encerrada")

# Instância única para ser usada no server.py e bootstrap
mongo_connection = MongoDBConnection()