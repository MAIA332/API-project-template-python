import asyncio
import json
import os
import websockets
import datetime
import bcrypt
from jose import jwt, JWTError, ExpiredSignatureError

class WebSocketServer:
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.clients = {}  # websocket -> {"username": ..., "room": ...}
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

    async def _emit(self, event, websocket, payload):
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

    async def _handle_ping(self, websocket, payload):
        """Responde ao cliente que enviou um ping."""
        try:
            await websocket.send(json.dumps({
                "event": "pong",
                "timestamp": self._now(),
                "payload": payload  # opcional, pode devolver dados recebidos
            }))
        except Exception as e:
            print(f"[{self._now()}]Erro ao enviar pong: {e}")

    # ============== WebSocket Handler ==============
    async def handler(self, websocket):
        client_ip = websocket.remote_address[0]
        print(f"[{self._now()}]Cliente conectado: {client_ip}")
        

        try:
            async for raw_message in websocket:
                # dentro do loop de mensagens
                print(f"[{self._now()}]Mensagem recebida de {client_ip}: {raw_message}")
                try:
                    message = json.loads(raw_message)
                    event = message.get("event")
                    payload = message.get("payload")

                    if not event:
                        await websocket.send(json.dumps({"error": "Campo 'event' é obrigatório"}))
                        continue

                    if not self.clients.get(websocket, {}).get("authenticated", False) and event != "auth":
                        await websocket.send(json.dumps({
                            "event": "error",
                            "message": f"Evento '{event}' não permitido antes da autenticação"
                        }))
                        continue
                    await self._emit(event, websocket, payload)

                except json.JSONDecodeError:
                    await websocket.send(json.dumps({"error": "JSON inválido"}))

        except websockets.exceptions.ConnectionClosedError:
            print(f"[{self._now()}]Conexão encerrada com {client_ip}")
        finally:
            print(f"[{self._now()}]Cliente desconectado: {client_ip}")
            await self._disconnect(websocket)
    

    async def notify_user(self, user_id: str, message: str,event:str):
        for ws, info in self.clients.items():
            # Decodifica token do cliente para pegar user_id (sub) ou já armazene user_id diretamente ao autenticar
            token = info.get("access_token")
            if not token:
                continue
            try:
                payload = jwt.decode(token, os.getenv("ACCESS_SECRET_KEY"), algorithms=["HS256"])
                if payload.get("sub") == user_id:
                    await ws.send(json.dumps({"event": event, "message": message}))
            except Exception as e:
                print(f"Erro decodificando token para notificar: {e}")

    async def _disconnect(self, websocket):
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
        targets = self.rooms.get(room, set()) if room else self.clients.keys()
        to_remove = set()
        for client in targets:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                to_remove.add(client)
        for client in to_remove:
            await self._disconnect(client)

    def _now(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async def start(self):
        print(f"Servidor WebSocket rodando em ws://{self.host}:{self.port}")
        async with websockets.serve(self.handler, self.host, self.port):
            await asyncio.Future()  # roda para sempre