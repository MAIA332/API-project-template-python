from prisma.errors import UniqueViolationError, ForeignKeyViolationError
from prisma.models  import User
from starlette.responses import JSONResponse
import bcrypt
import base64

class UserService:    
    def __init__(self, prisma, ws_server):
        self.prisma = prisma
        self.ws_server = ws_server

    async def create_(self, user_data: dict):
        try:
            # 1. Tratar a senha com bcrypt
            password_raw = user_data.get('password')
            password_hash = bcrypt.hashpw(password_raw.encode('utf-8'), bcrypt.gensalt(12))
            password_hash_base64 = base64.b64encode(password_hash).decode('utf-8')

            # 2. Buscar a Role pelo identifier para obter o idRole e validar o idSector
            # O schema exige que a Role pertença ao setor correto (relação composta)
            role = await self.prisma.role.find_unique(
                where={'identifier': user_data.get('role_identifier')},
                include={'Sector': True}
            )

            if not role:
                return JSONResponse(content={"message": "Role identifier not found."}, status_code=404)

            # Preparar dados para criação/atualização
            user_payload = {
                "email": user_data.get('email'),
                "name": user_data.get('name'),
                "description": user_data.get('description'),
                "password": password_hash_base64,
                "profileImage": user_data.get('profileImage'),
                "phoneNumber": user_data.get('phoneNumber'),
                "idSector": role.idSector, # Vincula ao setor da Role encontrada
                "idRole": role.id,
            }

            # 3. Executar o UPSERT
            # O email é o identificador único para o upsert
            upserted_user = await self.prisma.user.upsert(
                where={'email': user_payload['email']},
                data={
                    'create': user_payload,
                    'update': {k: v for k, v in user_payload.items() if k != 'email'}
                }
            )

            return upserted_user

        except ForeignKeyViolationError as e:
            # Tratamento de erro de integridade referencial baseado no seu schema
            return JSONResponse(content={"message": "Invalid Sector or Role relation."}, status_code=400)
        
        except Exception as e:
            print(f"Error on user upsert: {e}")
            return JSONResponse(content={"message": "Internal server error."}, status_code=500)
    async def getSelf(self):
        pass