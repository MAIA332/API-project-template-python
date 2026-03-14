import asyncio

class WorkerDTO:
    def __init__(self, mongo_client=None, ws=None, worker_config=None, prisma=None):
        self.mongo_client = mongo_client
        self.ws = ws
        self.prisma = prisma
        self.name = worker_config.get("name", "UnnamedWorker") if worker_config else "UnnamedWorker"
        self.description = worker_config.get("description", "") if worker_config else ""
        self.event = worker_config.get("event", "") if worker_config else ""
        self.updateRate = worker_config.get("update_rate", 60) if worker_config else 60
        self.createdAt = worker_config.get("createdAt", None) if worker_config else None
        self.updatedAt = worker_config.get("updatedAt", None) if worker_config else None
        self.beginDate = worker_config.get("beginDate", None) if worker_config else None
        self.endDate = worker_config.get("endDate", None) if worker_config else None
        self.dbName = worker_config.get("dbName", None) if worker_config else None
        self.subscribed_events = {}  
        
        self._name = self.__class__.__name__

        self.ws._on(self.event, self.run)
        #asyncio.create_task(self._on_event(self.event, self.run))

    async def _emit_event(self, event_name, data):
        if self.ws:
            print(f"[{self._name}] 📢 Emitindo evento '{event_name}' com dados: {data}")
            await self.ws.send_json({"event": event_name, "data": data})
        else:
            print(f"[{self._name}] ❌ WebSocket não disponível. Não foi possível emitir o evento '{event_name}'.")  

    async def _on_event(self, event_name, callback):
        if self.ws:
            print(f"[{self._name}] 🎧 Registrando ouvinte (callback) para o evento '{event_name}'.")
            self.subscribed_events[event_name] = callback
        else:
            print(f"[{self._name}] ❌ WebSocket não disponível. Não foi possível registrar o callback para '{event_name}'.")

    async def get_data_from_mongo(self, db_name, collection_name,date_range=None,date_field="date"):
        if self.mongo_client:
            db = self.mongo_client[db_name]
            collection = db[collection_name]
            
            query = {}
            if date_range:
                query[date_field] = {
                    "$gte": date_range["start"],
                    "$lte": date_range["end"]
                }
                print(f"[{self._name}] Consulta MongoDB com filtro de data: {query}")
            data = await collection.find(query).to_list(length=None)
            
            print(f"[{self._name}] Dados obtidos do MongoDB: {len(data)} registros.")
            return data
        else:
            print(f"[{self._name}] ❌ MongoDB client não disponível. Verifique a configuração.")
            return []
        
    async def _scheduler_loop(self):
        while True:
            if hasattr(self, 'run'):
                await self.run()
            else:
                print(f"[{self._name}] ⚠️ Método 'run()' não implementado na classe filha.")
                
            print(f"[{self._name}] ⏳ Aguardando {self.updateRate}s para o próximo ciclo...")
            await asyncio.sleep(self.updateRate)
        
    async def schedule(self):
        print(f"[{self._name}] Inicializando Worker (Evento base: {self.event}).")
        
        if self.updateRate > 0:
            print(f"[{self._name}] ⏱️ Agendando loop para rodar a cada {self.updateRate} segundos.")
            self._task = asyncio.create_task(self._scheduler_loop())
        else:
            print(f"[{self._name}] 🛑 Configurado como reativo/manual (update_rate=0). Não rodará em loop de tempo.")