import os
import time
import socket
import logging
import asyncio
import inspect
import importlib
import warnings
import traceback
from dotenv import load_dotenv

from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster
from cassandra.policies import RoundRobinPolicy
from cassandra.cqlengine import connection
from cassandra.cqlengine.management import sync_table, drop_table
from cassandra import InvalidRequest, AuthenticationFailed
from cassandra.query import SimpleStatement

load_dotenv()

class CassandraQueryBuilder:
    """Mantido o seu QueryBuilder original de forma limpa"""
    def __init__(self):
        self.initializers = {
            "get": "SELECT %s FROM %s WHERE %s",
            "insert": "INSERT INTO",
            "get_simple": "SELECT %s FROM %s"
        }

    def validate_inputs(self, table: str, whereInput: dict = None, args: dict = None, function_name: str = None):
        if function_name not in list(self.initializers.keys()):
            raise ValueError(f"Function '{function_name}' is not supported")
        if not table:
            raise ValueError("Table name is required")
        if whereInput and not isinstance(whereInput, dict):
            raise ValueError("whereInput must be a dictionary")
        if args and not isinstance(args, dict):
            raise ValueError("args must be a dictionary")

    def get(self, table, whereInput=None, select_fields=None):
        query_template = self.initializers["get"] if whereInput else self.initializers["get_simple"]
        fields = ", ".join(select_fields) if select_fields else "*"
        conditions = []
        values = []
        if whereInput:
            for k, v in whereInput.items():
                conditions.append(f"{k} = %s")
                values.append(v)
            where_clause = " AND ".join(conditions)
            query_str = query_template % (fields, table, where_clause)
        else:
            query_str = query_template % (fields, table)
        return SimpleStatement(query_str), tuple(values)


class CassandraConnection:
    def __init__(self):
        # 1. Busca configurações do .env
        hosts_env = os.getenv("CASSANDRA_HOSTS", "127.0.0.1")
        self.hosts = [h.strip() for h in hosts_env.split(",")]
        self.port = int(os.getenv("CASSANDRA_PORT", 9042))
        self.username = os.getenv("CASSANDRA_USER", "cassandra")
        self.password = os.getenv("CASSANDRA_PASSWORD", "cassandra")
        self.keyspace = os.getenv("CASSANDRA_KEYSPACE", "meu_keyspace")
        
        # Comportamentos do ORM via .env
        self.auto_migrate = os.getenv("CASSANDRA_AUTO_MIGRATE", "True").lower() == "true"
        self.auto_drop = os.getenv("CASSANDRA_AUTO_DROP", "False").lower() == "true"

        self.cluster = None
        self.session = None
        self.query_builder = CassandraQueryBuilder()
        self.models = []

    async def connect(self):
        """Método de inicialização chamado pelo BootstrapApp"""
        print(f"🔄 [CASSANDRA] Conectando aos hosts: {self.hosts}")
        
        # Como o Cassandra e as migrações podem bloquear o loop do FastAPI, 
        # rodamos o setup de forma segura em uma thread separada.
        await asyncio.to_thread(self._setup_connection_and_orm)

    def _setup_connection_and_orm(self):
        """Lógica síncrona de conexão e migração (ORM)"""
        max_retries = 5
        retry_delay = 5

        for host in self.hosts:
            if not self._wait_for_socket(host, self.port, max_retries, retry_delay):
                raise ConnectionError(f"❌ Cassandra em {host}:{self.port} não respondeu.")

        auth_provider = PlainTextAuthProvider(username=self.username, password=self.password)

        for attempt in range(1, max_retries + 1):
            try:
                self.cluster = Cluster(
                    contact_points=self.hosts,
                    port=self.port,
                    auth_provider=auth_provider,
                    connect_timeout=30.0,
                    load_balancing_policy=RoundRobinPolicy(),
                    protocol_version=5
                )
                self.session = self.cluster.connect()
                print(f"✅ [CASSANDRA] Conexão estabelecida na tentativa {attempt}.")
                break
            except Exception as e:
                logging.warning(f"⏳ Tentativa {attempt}/{max_retries} falhou: {e}")
                if attempt == max_retries:
                    raise
                time.sleep(retry_delay * attempt)

        # Keyspace Setup
        self._ensure_keyspace()
        
        # Registra o cqlengine (Obrigatório para o seu ORM funcionar)
        connection.register_connection(name='default', session=self.session)
        connection.set_default_connection('default')
        self.session.set_keyspace(self.keyspace)

        # Migrations Setup (Opcional via .env, default True)
        if self.auto_migrate:
            print("🚀 [CASSANDRA-ORM] Iniciando Migrations...")
            self.models = self._load_models_from_schema('models')
            self._sync_schema(self.models)
            self._drop_unused_tables(self.models)
            print("✅ [CASSANDRA-ORM] Migrations concluídas com sucesso.")

    def _wait_for_socket(self, host, port, max_retries, delay):
        for attempt in range(1, max_retries + 1):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(3)
                if sock.connect_ex((host, port)) == 0:
                    return True
                time.sleep(delay)
        return False

    def _ensure_keyspace(self, replication_class='SimpleStrategy', replication_factor=1):
        query = "SELECT keyspace_name FROM system_schema.keyspaces WHERE keyspace_name = %s"
        if not self.session.execute(query, (self.keyspace,)):
            print(f"🛠️ [CASSANDRA] Criando keyspace '{self.keyspace}'...")
            replication = f"{{'class': '{replication_class}', 'replication_factor': '{replication_factor}'}}"
            query_create = f"CREATE KEYSPACE IF NOT EXISTS {self.keyspace} WITH replication = {replication} AND durable_writes = true"
            self.session.execute(query_create)

    # ==================== LÓGICA DE ORM / MIGRATIONS ====================

    def _load_models_from_schema(self, module_name: str):
        # A string abaixo deve refletir o caminho exato do seu arquivo de models do Cassandra
        import_path = f"database.cassandra.{module_name}"
        try:
            module = importlib.import_module(import_path)
        except ModuleNotFoundError as e:
            logging.error(f"Erro ao importar '{import_path}': {e}")
            raise

        model_classes = []
        for name, func in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("create_") and name.endswith("_model"):
                try:
                    model = func(self.keyspace)
                    model_classes.append(model)
                except Exception as e:
                    logging.error(f"Erro ao carregar modelo '{name}': {e}")
        return model_classes

    def _sync_schema(self, models):
        for model in models:
            needs_drop = False
            warning_message = ""

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                sync_table(model) # Cria ou atualiza as colunas da tabela

                for warn in w:
                    msg = str(warn.message)
                    if "has column" in msg and "differing from the model type" in msg:
                        warning_message = msg
                        needs_drop = True

            if needs_drop:
                print(f"⚠️ [CASSANDRA-ORM] Tipo divergente na tabela '{model.__table_name__}': {warning_message}")
                # Aqui removemos o "input()", pois bloqueia o FastAPI de subir. Ele lê o .env
                if self.auto_drop:
                    print(f"🗑️ [CASSANDRA-ORM] AUTO_DROP ativado. Recriando tabela '{model.__table_name__}'...")
                    drop_table(model)
                    sync_table(model)
                    print(f"✅ [CASSANDRA-ORM] Tabela '{model.__table_name__}' recriada.")
                else:
                    print(f"⛔ [CASSANDRA-ORM] AUTO_DROP desativado. Altere manualmente ou mude CASSANDRA_AUTO_DROP=True no .env.")

    def _drop_unused_tables(self, models):
        model_table_names = {model.__table_name__ for model in models}
        existing_tables = self.session.cluster.metadata.keyspaces[self.keyspace].tables
        
        for table_name in list(existing_tables):
            if table_name not in model_table_names:
                # Segurança: Nunca dropar tabelas do próprio Cassandra ou Views nativas
                if not table_name.startswith("system") and self.auto_drop:
                    print(f"🧹 [CASSANDRA-ORM] Removendo tabela órfã: {table_name}")
                    query = f"DROP TABLE IF EXISTS {self.keyspace}.{table_name}"
                    self.session.execute(query)

    # ==================== MÉTODOS PÚBLICOS ====================
    def execute_query(self, query: str, parameters: tuple = None):
        try:
            return self.session.execute(query, parameters) if parameters else self.session.execute(query)
        except Exception as e:
            logging.error(f"❌ Erro ao executar query: {e}")
            raise

    def disconnect(self):
        if self.cluster:
            self.cluster.shutdown()
            print("🔌 [CASSANDRA] Conexão encerrada.")