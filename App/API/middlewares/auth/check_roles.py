#from database.prisma import prisma_connection
from fastapi import Request, HTTPException

async def check_roles(request: Request):
    path = request.url.path.split('/')[1]
    prisma_connection = request.app.state.prisma
    permitted_roles = await prisma_connection.route.find_first(
        where={
            'path': {
                'contains': path
            }
        },
        include={
            'roles': True
        }
    )
    
    user = await prisma_connection.user.find_unique(
        where={
            'id': request.state.user_id
        },
        include={
            'role': True
        }
    )
    
    if not user:
        raise HTTPException(detail={'message': 'Not Authorized.'}, status_code=401)

    for role in permitted_roles.roles:
        print(role.identifier, user.role.identifier)
        if role.identifier == user.role.identifier:
            return None

    raise HTTPException(detail={'message': 'You do not have permission to access this feature'}, status_code=401)