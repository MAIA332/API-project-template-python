import importlib

class IntegrationFactory:
    def __init__(self, mongo_client=None,prisma=None):
        self.instances = {}
        self.mongo = mongo_client
        self.prisma = prisma
        self.dependency_map = {"mongo": self.mongo, "prisma": self.prisma}
        self.instances = {}

    async def scrap_and_load(self):
        integrations = await self.prisma.integrations.find_many(where={"active": True},include={"parameters": True})
        for integration in integrations:
            module = importlib.import_module(f"integrations.{integration.name}.{integration.module}")
            integration_class = getattr(module, integration.entryPoint)
            parameters_mapped = {}
            for p in integration.parameters:
                if p.name in self.dependency_map:
                    parameters_mapped[p.name] = self.dependency_map[p.name]
                
            self.instances[integration.name] = integration_class(**parameters_mapped)

    async def get_integration(self, integration_name):
        return self.instances[integration_name]
