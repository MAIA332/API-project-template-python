import importlib
from fastapi import APIRouter
import os, sys
current_dir = os.path.dirname(os.path.abspath(__file__))
app_root = os.path.abspath(os.path.join(current_dir, "../"))

if app_root not in sys.path:
    sys.path.insert(0, app_root)

import importlib
import asyncio
from fastapi import APIRouter

class BootstrapApp:
    def __init__(self, prisma_client, mongodb_client, ws_server):
        self.prisma = prisma_client
        self.mongo = mongodb_client
        self.ws = ws_server
        
        self.services = {}
        self.pipelines = {}
        self.controllers = {}
        self.routers = []
        self.integrations = {}
        self.workers = {}
        self.databases = {}
        self.dependency_map = {
            "prisma": self.prisma,
            "ws_server": self.ws
        }

    async def bootstrap(self, app):
        print("[BOOTSTRAP] Iniciando mapeamento do sistema...")
        
        # ---> INJETANDO O APP NO MAPA DE DEPENDÊNCIAS <---
        self.dependency_map["app"] = app 

        await self._instantiate_databases()
        
        # 5. Instanciar Integrations (Dependem de DB e WS, e podem usar Services se necessário)
        await self._instanciate_integrations()

        # 1. Instanciar Services (Dependem de DB e WS e agora do App)
        await self._instantiate_services()
        
        # 2. Instanciar Controllers (Dependem de Services)
        await self._instantiate_controllers()
        
        # 3. Instanciar Routers e registrar no FastAPI
        await self._instantiate_routers(app)
        
        # 6. Instanciar Workers (Dependem de DB e WS, e podem usar Services se necessário)
        await self._intanciate_workers()
        
        print("[BOOTSTRAP] Sistema carregado com sucesso.")

    async def _instantiate_databases(self):
        # Busca apenas os bancos ativos na tabela Databases
        db_configs = await self.prisma.databases.find_many(
                    where={
                        "active": True,
                        "name": {
                            "not": "prisma"
                        }
                    }
                )        
        for db_conf in db_configs:
            print(f" -> Carregando Database Engine: {db_conf.name}")
            try:
                module = importlib.import_module(db_conf.module)
                db_class = getattr(module, db_conf.entryPoint)
                
                # Instancia a classe do banco
                db_instance = db_class() 
                
                # 1. Executa a conexão (se a classe tiver um método assíncrono de connect)
                if hasattr(db_instance, 'connect') and asyncio.iscoroutinefunction(db_instance.connect):
                    await db_instance.connect()
                    
                # 2. Armazena a instância no dicionário de controle de bancos
                self.databases[db_conf.name] = db_instance
                
                # 3. Injeta a própria instância da classe no mapa principal de dependências (ex: mapeia "mongo")
                self.dependency_map[db_conf.name] = db_instance
                
                # 4. Atribui dinamicamente à classe BootstrapApp (substitui o 'self.mongo = db_instance')
                # Assim, se o db_conf.name for "mongo", você poderá usar self.mongo em toda a classe
                setattr(self, db_conf.name, db_instance)
                
                # 5. Injeção de Client Bruto Dinâmico: 
                # Se a classe instanciada tiver a propriedade 'client', criamos a dependência com o sufixo '_client'
                if hasattr(db_instance, 'client') and db_instance.client is not None:
                    self.dependency_map[f"{db_conf.name}_client"] = db_instance.client

                print(f"    [OK] {db_conf.name} conectado e mapeado.")
            except Exception as e:
                print(f"    [ERROR] Falha ao carregar banco {db_conf.name}: {e}")

    async def _instantiate_services(self):
        # 1. Busca todos os serviços no banco
        db_services = await self.prisma.services.find_many(
            where={"active": True},
            include={"parameters": True}
        )
        
        # Dicionário de serviços que ainda precisam ser instanciados
        pending_services = {s.name: s for s in db_services}
        
        # Controle para evitar loop infinito em caso de dependência circular (A depende de B, que depende de A)
        max_attempts = len(pending_services) * 2
        attempts = 0

        while pending_services and attempts < max_attempts:
            attempts += 1
            
            # Usamos list() para iterar sobre uma cópia das chaves e poder modificar o dicionário original
            for s_name in list(pending_services.keys()):
                s = pending_services[s_name]
                
                module = importlib.import_module(f"API.services.{s.module}")
                service_class = getattr(module, s.entryPoint)
                
                parameters_mapped = {}
                can_instantiate = True
                
                for p in s.parameters:
                    # a) Core dependencies (Prisma, App, Mongo, WS)
                    if p.name in self.dependency_map:
                        parameters_mapped[p.name] = self.dependency_map[p.name]
                        
                    # b) Inter-service dependencies (Já carregados com sucesso nesta ou em rodadas anteriores)
                    elif p.name in self.services:
                        parameters_mapped[p.name] = self.services[p.name]
                        
                    # c) Integrações (MelhorEnvio, MercadoPago, SMTP, etc)
                    elif self.integrations and hasattr(self.integrations, 'instances') and p.name in self.integrations.instances:
                        parameters_mapped[p.name] = self.integrations.instances[p.name]
                        
                    # d) Dependência não resolvida ainda
                    else:
                        # Verifica se o serviço exigido está na fila de pendentes
                        if p.name in pending_services:
                            can_instantiate = False  # PAUSA! Adia a instanciação deste serviço para a próxima rodada
                            break
                        else:
                            # Se não está nem na fila, é uma dependência realmente ausente (Apenas avisa)
                            print(f" [WARNING] Dependência '{p.name}' para '{s.name}' não existe no banco. Passando None.")
                            parameters_mapped[p.name] = None
                
                # Se todas as dependências foram resolvidas, instancia o serviço!
                if can_instantiate:
                    print(f" -> Carregando Service: {s.name} [OK]")
                    self.services[s.name] = service_class(**parameters_mapped)
                    del pending_services[s.name] # Remove da fila de pendentes
                    
        # Se após o loop ainda houver serviços pendentes, temos um erro grave
        if pending_services:
            failed_list = ", ".join(pending_services.keys())
            raise Exception(f"Falha de Injeção de Dependências! Dependência Circular ou Serviço Inexistente bloqueou o carregamento de: {failed_list}")

    async def _instantiate_controllers(self):
        db_controllers = await self.prisma.controllers.find_many(
            where={"active": True},
            include={"services": True}
        )
        
        for c in db_controllers:
            print(f" -> Carregando Controller: {c.name}")
            module = importlib.import_module(f"API.controllers.{c.module}")
            controller_class = getattr(module, c.entryPoint)
            
            # Mapeia os serviços que este controller precisa
            required_services = {s.name: self.services[s.name] for s in c.services}
            
            self.controllers[c.name] = controller_class(**required_services)

    async def _instantiate_routers(self, app):
        db_routers = await self.prisma.routers.find_many(
            where={"active": True},
            include={"Controllers": True}
        )
        
        for r in db_routers:
            print(f" -> Registrando Router: {r.name} em {r.endpoint}")
            
            try:
                module = importlib.import_module(f"API.routes.{r.module}")
                router_init_func = getattr(module, r.entryPoint)
                
                # Pega a instância do controller vinculada a este router
                controller_instance = self.controllers[r.Controllers.name]
                
                # Inicializa a rota injetando o controller
                router_instance = router_init_func(controller_instance)
                
                app.include_router(router_instance, prefix=r.endpoint)

                print(f" -> Router registrado: {r.name} em {r.endpoint}")
            except Exception as e:
                print(e)

    async def _instanciate_integrations(self):
        module = importlib.import_module(f"integrations.factory")
        factory_class = getattr(module, "IntegrationFactory")
        facorty_instance = factory_class(mongo_client=self.mongo,prisma=self.prisma)
        await facorty_instance.scrap_and_load()
        self.integrations = facorty_instance

    async def _intanciate_workers(self):
        db_workers = await self.prisma.workers.find_many()
        for w in db_workers:
            print(f" -> Carregando Worker: {w.name}")
            module = importlib.import_module(f"Workers.factory")
            factory_class = getattr(module, "WorkerFactory")
            
            # Garanta que estamos passando o objeto ou um dict válido
            worker_config = w.dict() if hasattr(w, 'dict') else w.__dict__
            
            factory = factory_class(
                mongo_client=self.mongo, 
                ws=self.ws,
                worker_config=worker_config,
                prisma=self.prisma,
                integrations=self.integrations
            )
            
            worker_instance = factory.create_worker()
            
            if worker_instance:
                await worker_instance.schedule()
                self.workers[w.name] = worker_instance
            else:
                print(f" [ERROR] Falha ao instanciar worker: {w.name}")