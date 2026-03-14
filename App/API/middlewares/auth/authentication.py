from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from jose import jwt, JWTError, ExpiredSignatureError
import os

class AuthenticationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app,prisma):
        super().__init__(app)
        self.prisma = prisma
    
    async def dispatch(self, request: Request, call_next):
        print("AuthenticationMiddleware: Checking authentication")
        if request.url.path in ["/docs", "/redoc", "/openapi.json", "/auth/login", "/auth/login/","/advises/integration/meta/webhook"]:
            response = await call_next(request)
            return response
        
        authorization = request.headers.get("Authorization")
        
        if not authorization:
            return JSONResponse(content={'message': 'Token was not provided.'}, status_code=401)
            
        try:
            auth_type, token = authorization.split(" ")
            
            if auth_type != "Bearer" or not token:
                return JSONResponse(content={'message': 'Not Authorized.'}, status_code=401)

            payload = jwt.decode(token, os.getenv("ACCESS_SECRET_KEY"), algorithms=["HS256"])
            
            user_id = payload.get("sub")
            
            request.state.user_id = user_id

            if not user_id:
                return JSONResponse(content={'message': 'Not Authorized.'}, status_code=401)
         
        except ExpiredSignatureError as e:
            return JSONResponse(content={'message': 'Token expired.'}, status_code=401)
        
        except (ValueError, JWTError) as e:
            return JSONResponse(content={'message': 'Invalid Token.'}, status_code=401)

        except Exception as e:
            return JSONResponse(content={'message': 'Internal Server Error.'}, status_code=500)
        
        response = await call_next(request)
        return response