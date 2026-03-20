import asyncio
import json
from starlette.responses import JSONResponse
from datetime import datetime, timedelta
import bcrypt
from jose import jwt, JWTError, ExpiredSignatureError
import os
import base64

class AuthService:
    def __init__(self,prisma=None,ws_server=None):
        self.secret_key = os.getenv("ACCESS_SECRET_KEY")
        self.refresh_key = os.getenv("REFRESH_SECRET_KEY")
        self.prisma = prisma
        self.ws = ws_server
        self.listeners = {}
        self._subscriber()
    # ============== Observer Pattern ==============   
  
    
    def _subscriber(self):
        self.ws._on("auth", self.handle_ws_auth)
        pass
    
    def _on(self, event, callback):
        print(f"Adding listener for event: {event}")
        if event not in self.listeners:
            self.listeners[event] = []
        self.listeners[event].append(callback)
        
    async def _emit(self, event, *args, **kwargs):
        print(f"Emitting event: {event}")
        if event in self.listeners:
            for callback in self.listeners[event]:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args, **kwargs)
                else:
                    callback(*args, **kwargs)
                
    def _off(self, event, callback):
        if event in self.listeners:
            self.listeners[event].remove(callback)

    async def test(self):
        print("AuthService test method called")
        return "AuthService is working!"
    
    async def checkAuth(self,token):
        try:
            auth_type, token = token.split(" ")
            
            if auth_type != "Bearer" or not token:
                return JSONResponse(content={'message': 'Not Authorized.'}, status_code=401)

            payload = jwt.decode(token, os.getenv("ACCESS_SECRET_KEY"), algorithms=["HS256"])
            
            user_id = payload.get("sub")

            user = await self.prisma.user.find_first(
                where={
                    'id': user_id
                },
                include={
                    'Role': {
                        'include': {
                            'Route': True
                        }
                    },
                    'Sector': True
                        
                }
            )

            if not user:
                return JSONResponse(content={'message': 'User do not exists'}, status_code=401)

            else:
                return user

        except Exception as e:
            return False

    # ==================================================
    # ============== Events handlers ===================
    async def handle_ws_auth(self, websocket, payload):
        """
        Handler para autenticação WebSocket. Espera:
        {
            "event": "auth",
            "payload": {
                "email": "...",
                "password": "...",
                "room": "opcional"
            }
        }
        """
        email = payload.get("email")
        password = payload.get("password")
        room = payload.get("room")

        if not email or not password:
            jwtToken = payload.get("jwtToken")
            if not jwtToken:
                await websocket.send(json.dumps({"error": "Credenciais incompletas"}))
                return
            else:
                isValidAuth = await self.checkAuth(jwtToken)
                if isValidAuth:
                    # Salva cliente no servidor WebSocket
                    self.ws.clients[websocket] = {
                        "email": isValidAuth.email,
                        "username": isValidAuth.name,
                        "role": isValidAuth.Role.identifier,
                        "sector": isValidAuth.Sector.name,
                        "room": room,
                        "access_token":jwtToken.split(" ")[1],
                        "authenticated":True
                    }

                    if room:
                        self.ws.rooms.setdefault(room, set()).add(websocket)

                    # Envia confirmação ao cliente
                    await websocket.send(json.dumps({
                        "status": "authenticated",
                        "user": {
                            "name": isValidAuth.name,
                            "email": isValidAuth.email,
                            "role":  isValidAuth.Role.identifier,
                            "sector": isValidAuth.Sector.name
                        },
                        #"access_token": result["access_token"],
                        "room": room
                    }))
                    return

        # Autentica via método reutilizável
        try:
            result = await self.authenticate(email, password)
        except Exception as e:
            print("Erro interno:", e)
            await websocket.send(json.dumps({"error": "Erro interno ao autenticar"}))
            return

        # Se retorno for JSONResponse (erro), converte para WebSocket resposta
        if isinstance(result, JSONResponse):
            await websocket.send(json.dumps({"error": result.body.decode()}))
            return

        # Salva cliente no servidor WebSocket
        self.ws.clients[websocket] = {
            "email": result["email"],
            "username": result["name"],
            "role": result["role"],
            "sector": result["sector"],
            "room": room,
            "access_token":result["access_token"],
            "authenticated":True
        }

        if room:
            self.ws.rooms.setdefault(room, set()).add(websocket)

        # Envia confirmação ao cliente
        await websocket.send(json.dumps({
            "status": "authenticated",
            "user": {
                "name": result["name"],
                "email": result["email"],
                "role": result["role"],
                "sector": result["sector"]
            },
            #"access_token": result["access_token"],
            "room": room
        }))
    
    async def authenticate(self, email, password):
            try:
                # Busca o usuário, incluindo papel e setor (com relações compostas)
                user = await self.prisma.user.find_first(
                    where={
                        'email': email
                    },
                    include={
                        'Role': {
                            'include': {
                                'Route': True  # Para acessar as rotas permitidas via Role
                            }
                        },
                        'Sector': True
                            
                    }
                )

                if not user:
                    return JSONResponse(content={'message': 'User do not exists'}, status_code=401)

                db_password = base64.b64decode(user.password)
                password_matched = bcrypt.checkpw(password.encode('utf-8'), db_password)

                if not password_matched:
                    return JSONResponse(content={'message': 'User or pass incorrect.'}, status_code=401)

                # Geração dos tokens JWT
                access_token = jwt.encode(
                    {"sub": user.id, "exp": datetime.utcnow() + timedelta(days=60)},
                    self.secret_key,
                    algorithm="HS256"
                )

                refresh_token = jwt.encode(
                    {"sub": user.id, "exp": datetime.utcnow() + timedelta(hours=9)},
                    self.refresh_key,
                    algorithm="HS256"
                )

                # Coleta das rotas permitidas via relação many-to-many entre Role <-> Route
                permited_routes_paths = [route.path for route in user.Role.Route]

                return {
                    'name': user.name,
                    'description': user.description,
                    'email': user.email,
                    'phone_number': user.phoneNumber,
                    'role': user.Role.identifier,
                    'sector': user.Sector.name,
                    'permited_routes': permited_routes_paths,
                    'access_token': access_token,
                    'refresh_token': refresh_token
                }

            except Exception as e:
                print("Erro durante autenticação:", e)
                return JSONResponse(content={'message': 'Occur an error to login. Try again later.'}, status_code=500)