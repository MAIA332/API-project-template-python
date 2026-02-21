import importlib
from fastapi import APIRouter

class BootstrapApp:
    def __init__(self, prisma_client, mongodb_client, ws_server):
        self.prisma = prisma_client
        self.mongo = mongodb_client
        self.ws = ws_server
        
        self.services = {}
        self.controllers = {}
        self.routers = []
        self.dependency_map = {
            "prisma": self.prisma,
            "mongo": self.mongo,
            "ws_server": self.ws
        }

    async def bootstrap(self, app):
        print("[BOOTSTRAP] Iniciando mapeamento do sistema...")
        
        # 1. Instanciar Services (Dependem de DB e WS)
        await self._instantiate_services()
        
        # 2. Instanciar Controllers (Dependem de Services)
        await self._instantiate_controllers()
        
        # 3. Instanciar Routers e registrar no FastAPI
        await self._instantiate_routers(app)
        
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
            # Usamos o nome salvo no banco para buscar a instância no dependency_map
            parameters_mapped = {}
            for p in s.parameters:
                if p.name in self.dependency_map:
                    parameters_mapped[p.name] = self.dependency_map[p.name]
                else:
                    print(f" [WARNING] Dependência '{p.name}' não encontrada no mapa para o serviço {s.name}")

            # 3. Injeta as dependências mapeadas (prisma, mongo, ws_server)
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