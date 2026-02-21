from fastapi import APIRouter, Body, Request
from ..models.users import UserCreateInput
from prisma.models import User

user_router = APIRouter()

# Esta função será chamada no seu bootstrap_app.py ou server.py
# para injetar as dependências corretamente
def init_user_routes(user_controller):
    
    @user_router.post("/", response_model=User, status_code=201)
    async def create(user: UserCreateInput = Body(...)):
        # Chama o controller que, por sua vez, chama o service
        return await user_controller.create(user)

    return user_router