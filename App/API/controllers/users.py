
from prisma.models import User
from ..models.users import UserCreateInput


class UserController:
    def __init__(self, UserService): 
        self.user_service = UserService
        
    async def create(self, user: UserCreateInput):
        data = user.model_dump()
        user = await self.user_service.create_(data)
        return user