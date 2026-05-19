from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from jose import jwt, JWTError, ExpiredSignatureError
import os

class AuthenticationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, prisma):
        super().__init__(app)
        self.prisma = prisma
        
        # Dicionário mapeando a rota para os métodos HTTP públicos.
        # Use "*" para liberar todos os métodos daquela rota.
        self.public_routes = {
            "/docs": ["*"],
            "/redoc": ["*"],
            "/openapi.json": ["*"],
            "/auth/login": ["POST"],
            "/auth/login/": ["POST"]
        }
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method
        
        print(f"AuthenticationMiddleware: Checking authentication for {method} {path}")
        
        # 1. Verificação combinada de Rota + Método
        if path in self.public_routes:
            allowed_methods = self.public_routes[path]
            
            # Se a configuração permite qualquer método ("*") ou o método exato da requisição
            if "*" in allowed_methods or method in allowed_methods:
                return await call_next(request)
        
        # 2. Início do fluxo de Autenticação para rotas protegidas
        authorization = request.headers.get("Authorization")
        
        if not authorization:
            return JSONResponse(content={'message': 'Token was not provided.'}, status_code=401)
            
        try:
            auth_type, token = authorization.split(" ")
            
            if auth_type != "Bearer" or not token:
                return JSONResponse(content={'message': 'Not Authorized.'}, status_code=401)

            payload = jwt.decode(token, os.getenv("JWT_SECRET_KEY"), algorithms=["HS256"])
            
            user_id = payload.get("sub")
            
            if not user_id:
                return JSONResponse(content={'message': 'Not Authorized.'}, status_code=401)
                
            request.state.user_id = user_id
         
        except ExpiredSignatureError:
            return JSONResponse(content={'message': 'Token expired.'}, status_code=401)
        
        except (ValueError, JWTError):
            return JSONResponse(content={'message': 'Invalid Token.'}, status_code=401)

        except Exception as e:
            print(f"AuthenticationMiddleware Error: {e}")
            return JSONResponse(content={'message': 'Internal Server Error.'}, status_code=500)
        
        response = await call_next(request)
        return response