import math
import pandas as pd
from .workerDTO import WorkerDTO
import asyncio
from datetime import datetime, timezone, timedelta, time
import json
import os
import inspect
from .alerts.alert_handlers import AlertFactory

class AlertWorker(WorkerDTO):
    def __init__(self, mongo_client=None, ws=None, worker_config=None, prisma=None, integrations=None):
        super().__init__(mongo_client, ws, worker_config, prisma)
        
        # Configurações parametrizáveis com valores padrão genéricos
        self.worker_config = worker_config or {}
        self.logs_collection = self.worker_config.get("logs_collection", "alert_logs")
        self.registers_collection = self.worker_config.get("registers_collection", "alert_registers")
        self.ws_event_name = self.worker_config.get("ws_event_name", "new_alert")
        self.check_interval = self.worker_config.get("check_interval", 60)
        
        # Configuração de Timezone (Default: UTC)
        tz_offset_hours = self.worker_config.get("tz_offset_hours", 0)
        self.tz = timezone(timedelta(hours=tz_offset_hours))
        
        self.integrations = integrations
        asyncio.create_task(self._on_event(self.event, self.run))
    
    async def run(self, websocket=None, payload=None, *args, **kwargs):
        print(f"[{datetime.now(self.tz)}] Iniciando AlertWorker...")
        
        # Inicialização agnóstica das coleções
        collections = await self.mongo_client[self.dbName].list_collection_names()
        if self.logs_collection not in collections:
            await self.mongo_client[self.dbName].create_collection(self.logs_collection)
        if self.registers_collection not in collections:
            await self.mongo_client[self.dbName].create_collection(self.registers_collection)

        self.logs_database = self.mongo_client[self.dbName][self.logs_collection]
        self.registers_database = self.mongo_client[self.dbName][self.registers_collection]

        while True:
            try:
                current_dt = datetime.now(self.tz)
                print(f"[{current_dt}] AlertWorker: Verificando alertas ativos...")
                
                # Busca de alertas genérica
                alerts = await self.prisma.alerts.find_many(
                    where={"active": True},
                    include={"Senders": True, "target": True,"type": True}
                )
                
                for alert in alerts:
                    await self.process_alert(alert)

            except Exception as e:
                print(f"[{datetime.now(self.tz)}] Erro no ciclo de verificação do AlertWorker: {e}")
            
            await asyncio.sleep(self.check_interval)

    async def process_alert(self, alert):
        try:
            # 1. Solicita o manipulador correto para a Factory
            handler = AlertFactory.get_handler(alert.type, self)
        except ValueError as e:
            print(f"\033[93m[AVISO] {e}\033[0m")
            return

        # 2. Verifica a condição usando a regra isolada na classe handler
        condition_met, context_data = await handler.verify(alert.condition or {})
        
        if not condition_met:
            return

        contexts_to_process = context_data if isinstance(context_data, list) else [context_data]
        should_trigger_alert = False
        
        # 3. Usa o cooldown dinâmico da própria classe handler
        threshold_time = datetime.now(timezone.utc) - timedelta(minutes=handler.cooldown_minutes) 

        for context in contexts_to_process:
            alert_hash = f"{alert.id}_{context.get('hash', 'default')}"
            already_sent = await self.registers_database.find_one({
                "alert_id": alert.id,
                "alert_hash": alert_hash,
                "triggered_at": {"$gte": threshold_time} 
            })
            
            if not already_sent:
                should_trigger_alert = True
                break

        if should_trigger_alert:
            ws_payload = {
                "alert_id": alert.id,
                "type": alert.type.name,
                "message": alert.message,
                "contexts": contexts_to_process, 
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            try:
                await self._emit_event(self.ws_event_name, ws_payload)
            except Exception as ws_err:
                print(f"[{datetime.now(self.tz)}] ❌ Erro ao emitir via WebSocket: {ws_err}")

            # Passa o handler junto para o envio
            await self.send_notification(alert, contexts_to_process, handler)
            
            # Registra a ocorrência do alerta
            registers_to_insert = [
                {
                    "alert_id": alert.id,
                    "alert_hash": f"{alert.id}_{ctx.get('hash', 'default')}",
                    "type": alert.type.name,
                    "triggered_at": datetime.now(timezone.utc),
                    "context": ctx,
                    "resolved": False
                } for ctx in contexts_to_process
            ]
            await self.registers_database.insert_many(registers_to_insert)

            # Loga a ação
            await self.logs_database.insert_one({
                "alert_id": alert.id,
                "action": "TRIGGERED_BATCH",
                "timestamp": datetime.now(timezone.utc),
                "batch_size": len(contexts_to_process)
            })

    async def send_notification(self, alert, context_data, handler):
        sender = getattr(alert, 'Senders', None)
        targets = getattr(alert, 'target', [])
        
        if not sender or not targets:
            return

        replace_dict = {}
        if isinstance(context_data, list):
            if len(context_data) == 1:
                replace_dict = context_data[0]
            else:
                # Formatação puramente genérica. A lógica de negócio fica no handler.
                formatted_items = [f"• {json.dumps(ctx, ensure_ascii=False)}" for ctx in context_data]
                
                replace_dict = {
                    "quantidade_alertas": len(context_data),
                    "payload": "\n".join(formatted_items) 
                }
                # Garante que os dados do primeiro contexto também estejam disponíveis
                if context_data:
                    for k, v in context_data[0].items():
                        if k not in replace_dict:
                            replace_dict[k] = v
        else:
            replace_dict = context_data

        integration_name = getattr(sender, 'name', None)
        if not integration_name:
            return

        integration_instance = self.integrations.instances.get(integration_name)

        if not integration_instance:
            print(f"\033[91m[ERRO] Integração '{integration_name}' não encontrada.\033[0m")
            return
        
        # ====================================================================
        # DISPARO DINÂMICO USANDO O HANDLER
        # ====================================================================
        for user in targets:
            try:
                # Busca flexível de informações de contato (ex: phone, email, contact)
                contact_info = getattr(user, 'phoneNumber', getattr(user, 'email', getattr(user, 'contact', None)))
                target_name = getattr(user, 'name', 'Usuário')
                
                if contact_info:
                    # Delega a montagem dos parâmetros do template para a classe específica
                    template_name, template_params = handler.get_notification_payload(target_name, replace_dict)
                    
                    # Usa kwargs para flexibilidade na integração
                    integration_payload = {
                        "phone": contact_info, # Mantido 'phone' por compatibilidade legada, idealmente trocaria para 'to' ou 'contact'
                        "template_name": template_name,
                        "template_params": template_params
                    }
                    
                    if asyncio.iscoroutinefunction(integration_instance.send):
                        await integration_instance.send(**integration_payload)
                    else:
                        integration_instance.send(**integration_payload)
                else:
                    print(f"\033[93mUsuário {target_name} não possui informação de contato cadastrada.\033[0m")            
            except Exception as e:
                print(f"\033[91m[ERRO] Falha ao enviar alerta para {getattr(user, 'name', 'Desconhecido')}: {e}\033[0m")