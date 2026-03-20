
class AuthController:
    def __init__(self, AuthService):
        self.auth_service = AuthService
        
    async def login(self, email, password):
        
        auth = await self.auth_service.authenticate(email, password)
        
        return auth
    
    async def test(self):
        return await self.auth_service.test()