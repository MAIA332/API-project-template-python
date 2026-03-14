import importlib

class WorkerFactory:
    def __init__(self, mongo_client=None,ws=None,worker_config=None,prisma=None,integrations=None):
        self.worker_config = worker_config
        self.mongo_client = mongo_client
        self.ws = ws
        self.prisma = prisma
        self.integrations = integrations
        #print(f"WorkerFactory initialized with config: {worker_config}")


    def create_worker(self):
        # Extrai os valores com segurança, garantindo que não são None antes de usar .lower()
        raw_module = self.worker_config.get('module')
        raw_entry_point = self.worker_config.get('entryPoint')
        
        # Se raw_module for None ou string vazia, usa 'default_worker'
        safe_module = raw_module.lower() if raw_module else 'default_worker'
        safe_entry_point = raw_entry_point if raw_entry_point else 'default_worker'
        
        module_name = f"Workers.{safe_module}"
        
        try:
            module = importlib.import_module(module_name)
            worker_class = getattr(module, safe_entry_point)
            
            return worker_class(
                mongo_client=self.mongo_client, 
                ws=self.ws, 
                worker_config=self.worker_config, 
                prisma=self.prisma,
                integrations=self.integrations
            )
        except (ImportError, AttributeError) as e:
            print(f"Erro ao criar worker {self.worker_config.get('name', 'Desconhecido')}: {e}")
            return None