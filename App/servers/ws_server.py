import asyncio
import json
import os
import datetime
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import WebSocket, WebSocketDisconnect

class WebSocketServer:
    def __init__(self):
        self.clients = {}  # websocket -> {"ip": ..., "authenticated": ..., "room": ..., "access_token": ...}
        self.rooms = {}    # room_name -> set(websockets)
        self.listeners = {}  # event_name -> list of callbacks
        self._subscriber()

    # ============== Observer Pattern ==============    
    def _subscriber(self):
        # Serviços externos devem usar self._on("event", callback)
        self._on("ping", self._handle_ping)

    def _on(self, event, callback):
        print(f"Adicionando listener para evento: {event}")
        if event not in self.listeners:
            self.listeners[event] = []
        self.listeners[event].append(callback)

    async def _emit(self, event, websocket: WebSocket, payload):
        print(f"[{self._now()}]Emitindo evento: {event}")
        if event in self.listeners:
            for callback in self.listeners[event]:
                if asyncio.iscoroutinefunction(callback):
                    await callback(websocket, payload)
                else:
                    callback(websocket, payload)

    def _off(self, event, callback):
        if event in self.listeners:
            self.listeners[event].remove(callback)

    async def _handle_ping(self, websocket: WebSocket, payload):
        """Responde ao cliente que enviou um ping."""
        try:
            await websocket.send_text(json.dumps({
                "event": "pong",
                "timestamp": self._now(),
                "payload": payload  # opcional, pode devolver dados recebidos
            }))
        except Exception as e:
            print(f"[{self._now()}]Erro ao enviar pong: {e}")

    # ============== WebSocket Handler ==============
    async def handler(self, websocket: WebSocket):
        await websocket.accept()  # Aceita a conexão nativa do FastAPI
        
        # O FastAPI mapeia o IP do cliente aqui
        client_ip = websocket.client.host if websocket.client else "Desconhecido"
        print(f"[{self._now()}]Cliente conectado: {client_ip}")
        
        self.clients[websocket] = {"ip": client_ip, "authenticated": True}
        
        try:
            while True:
                # O loop infinito que escuta as mensagens ativamente
                raw_message = await websocket.receive_text()
                print(f"[{self._now()}]Mensagem recebida de {client_ip}: {raw_message}")
                
                try:
                    message = json.loads(raw_message)
                    event = message.get("event")
                    payload = message.get("payload")

                    if not event:
                        await websocket.send_text(json.dumps({"error": "Campo 'event' é obrigatório"}))
                        continue

                    # Emite o evento internamente para os listeners
                    await self._emit(event, websocket, payload)

                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({"error": "JSON inválido"}))

        except WebSocketDisconnect:
            print(f"[{self._now()}]Conexão encerrada com {client_ip}")
        except Exception as e:
            print(f"[{self._now()}]Erro inesperado na conexão com {client_ip}: {e}")
        finally:
            print(f"[{self._now()}]Cliente desconectado: {client_ip}")
            await self._disconnect(websocket)
    
    async def notify_user(self, user_id: str, message: str, event: str):
        for ws, info in self.clients.items():
            token = info.get("access_token")
            if not token:
                continue
            try:
                payload = jwt.decode(token, os.getenv("ACCESS_SECRET_KEY"), algorithms=["HS256"])
                if payload.get("sub") == user_id:
                    await ws.send_text(json.dumps({"event": event, "message": message}))
            except Exception as e:
                print(f"Erro decodificando token para notificar: {e}")

    async def _disconnect(self, websocket: WebSocket):
        """Remove cliente do sistema e das salas."""
        info = self.clients.pop(websocket, None)
        if info and info.get("room"):
            room = info["room"]
            if room in self.rooms:
                self.rooms[room].discard(websocket)
                if not self.rooms[room]:
                    del self.rooms[room]

    async def broadcast(self, message: str, room: str = None):
        """Envia uma mensagem para todos os clientes ou apenas para uma sala."""
        targets = self.rooms.get(room, set()) if room else list(self.clients.keys())
        to_remove = set()
        
        for client in targets:
            try:
                await client.send_text(message)
            except Exception:
                to_remove.add(client)
                
        for client in to_remove:
            await self._disconnect(client)

    async def send_json(self, data: dict, room: str = None):
        """Converte um dicionário em JSON e envia via broadcast, tratando datas e timestamps."""
        try:
            def json_serial(obj):
                if hasattr(obj, 'isoformat'):
                    return obj.isoformat()
                raise TypeError(f"Tipo {type(obj)} não é serializável")

            message = json.dumps(data, default=json_serial)
            await self.broadcast(message, room=room)
        except Exception as e:
            print(f"[{self._now()}] Erro ao serializar JSON para envio: {e}")
    
    def _now(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")