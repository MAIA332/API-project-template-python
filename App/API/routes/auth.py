from fastapi import APIRouter, Body, Request
from ..models.auth import LoginInput, LoginResponse

auth_router = APIRouter()

# Esta função será chamada no seu bootstrap_app.py ou server.py
# para injetar as dependências corretamente
def init_auth_routes(auth_controller):
    
    @auth_router.post("/login", response_model=LoginResponse, status_code=201)
    async def login(data:LoginInput = Body(...)):
        # Chama o controller que, por sua vez, chama o service
        return await auth_controller.login(data.email, data.password)
    
    @auth_router.get("/test")
    async def test():
        return await auth_controller.test()

    return auth_router