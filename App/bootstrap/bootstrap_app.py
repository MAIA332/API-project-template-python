import importlib
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
        self.dependency_map = {
            "prisma": self.prisma,
            "mongo": self.mongo.client,
            "ws_server": self.ws
        }

    async def bootstrap(self, app):
        print("[BOOTSTRAP] Iniciando mapeamento do sistema...")
        
        # 5. Instanciar Integrations (Dependem de DB e WS, e podem usar Services se necessário)
        await self._instanciate_integrations()

        # 1. Instanciar Services (Dependem de DB e WS)
        await self._instantiate_services()
        
        # 2. Instanciar Controllers (Dependem de Services)
        await self._instantiate_controllers()
        
        # 3. Instanciar Routers e registrar no FastAPI
        await self._instantiate_routers(app)
        
        # 6. Instanciar Workers (Dependem de DB e WS, e podem usar Services se necessário)
        await self._intanciate_workers()
        
        print("[BOOTSTRAP] Sistema carregado com sucesso.")

    async def _instantiate_services(self):
        # 1. É necessário incluir a relação 'parameters' na busca
        db_services = await self.prisma.services.find_many(
            where={"active": True},
            include={"parameters": True}
        )
        
        for s in db_services:
            print(f" -> Carregando Service: {s.name}")
            
            # Ajuste do caminho do módulo conforme sua tree: App.API.services...
            module = importlib.import_module(f"API.services.{s.module}")
            service_class = getattr(module, s.entryPoint)
            
            # 2. Mapeia a lista de objetos Parameters para o dicionário de dependências
            parameters_mapped = {}
            for p in s.parameters:
                # a) Procura primeiro no mapa padrão (prisma, mongo, ws_server)
                if p.name in self.dependency_map:
                    parameters_mapped[p.name] = self.dependency_map[p.name]
                
                # b) Se não achar, procura nas Integrações carregadas pela Factory
                elif self.integrations and hasattr(self.integrations, 'instances') and p.name in self.integrations.instances:
                    parameters_mapped[p.name] = self.integrations.instances[p.name]
                
                # c) Se não existir em nenhum dos dois, emite o aviso
                else:
                    print(f" [WARNING] Dependência '{p.name}' não encontrada no mapa global nem nas integrações para o serviço {s.name}")

            # 3. Injeta as dependências mapeadas (prisma, mongo, ws_server, WAOFController, etc)
            self.services[s.name] = service_class(**parameters_mapped)

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
            module = importlib.import_module(f"API.routes.{r.module}")
            router_init_func = getattr(module, r.entryPoint)
            
            # Pega a instância do controller vinculada a este router
            controller_instance = self.controllers[r.Controllers.name]
            
            # Inicializa a rota injetando o controller
            router_instance = router_init_func(controller_instance)
            
            app.include_router(router_instance, prefix=r.endpoint)

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
