import asyncio
from prisma import Prisma

async def run_seed():
    prisma = Prisma()
    await prisma.connect()

    print("🚀 Iniciando Seed da Arquitetura (Bootstrap)...")

    # ==========================================
    # 0. DATABASES (Bancos de Dados Dinâmicos)
    # Tabela: Databases (prisma.databases)
    # ==========================================
    async def upsert_database(name, module, entry_point):
        d = await prisma.databases.find_first(where={"name": name})
        data = {
            "name": name,
            "module": module,
            "entryPoint": entry_point,
            "active": True
        }
        if d:
            return await prisma.databases.update(where={"id": d.id}, data=data)
        return await prisma.databases.create(data=data)

    # Exemplo: API/databases/mongo_db.py -> class MongoImplementation
    await upsert_database("mongo", "mongo_db", "MongoImplementation")
    # Exemplo: API/databases/cassandra_db.py -> class CassandraImplementation
    await upsert_database("cassandra", "cassandra_db", "CassandraImplementation")
    
    print("✅ Databases dinâmicos cadastrados.")

    # ==========================================
    # 1. PARÂMETROS BASE (Core Dependencies)
    # ==========================================
    # Note que agora 'mongo' e 'cassandra' são gerados na injeção dinâmica acima, 
    # mas precisamos cadastrá-los como parâmetros para que os services possam pedir!
    param_names = ["prisma", "ws_server", "mongo", "cassandra", "app"]
    param_map = {}
    
    for p_name in param_names:
        p = await prisma.parameters.find_first(where={"name": p_name})
        if not p:
            p = await prisma.parameters.create(data={"name": p_name})
        param_map[p_name] = p.id
        
    print("✅ Parâmetros base cadastrados.")

    # ==========================================
    # 2. SERVICES
    # ==========================================
    async def upsert_service(name, module, entry_point, param_ids):
        s = await prisma.services.find_first(where={"name": name})
        data = {
            "name": name,
            "module": module,
            "entryPoint": entry_point,
            "active": True,
            "parameters": {
                "connect": [{"id": pid} for pid in param_ids]
            }
        }
        if s:
            return await prisma.services.update(where={"id": s.id}, data=data)
        return await prisma.services.create(data=data)

    auth_service = await upsert_service(
        "AuthService", "auth", "AuthService",
        [param_map["prisma"], param_map["ws_server"]]
    )
    
    user_service = await upsert_service(
        "UserService", "users", "UserService",
        [param_map["prisma"], param_map["ws_server"]]
    )
    print("✅ Services cadastrados.")

    # ==========================================
    # 3. CONTROLLERS
    # ==========================================
    async def upsert_controller(name, module, entry_point, service_ids):
        c = await prisma.controllers.find_first(where={"name": name})
        data = {
            "name": name,
            "module": module,
            "entryPoint": entry_point,
            "active": True,
            "services": {
                "connect": [{"id": sid} for sid in service_ids]
            }
        }
        if c:
            return await prisma.controllers.update(where={"id": c.id}, data=data)
        return await prisma.controllers.create(data=data)

    auth_controller = await upsert_controller("AuthController", "auth", "AuthController", [auth_service.id])
    user_controller = await upsert_controller("UserController", "users", "UserController", [user_service.id])
    print("✅ Controllers cadastrados.")

    # ==========================================
    # 4. ROUTERS
    # ==========================================
    await prisma.routers.upsert(
        where={"endpoint": "/auth"},
        data={
            "create": {
                "name": "AuthRouter",
                "module": "auth",
                "entryPoint": "init_auth_routes",
                "endpoint": "/auth",
                "active": True,
                "controllersId": auth_controller.id
            },
            "update": {
                "name": "AuthRouter",
                "module": "auth",
                "entryPoint": "init_auth_routes",
                "active": True,
                "controllersId": auth_controller.id
            }
        }
    )

    await prisma.routers.upsert(
        where={"endpoint": "/users"},
        data={
            "create": {
                "name": "UserRouter",
                "module": "users",
                "entryPoint": "init_user_routes",
                "endpoint": "/users",
                "active": True,
                "controllersId": user_controller.id
            },
            "update": {
                "name": "UserRouter",
                "module": "users",
                "entryPoint": "init_user_routes",
                "active": True,
                "controllersId": user_controller.id
            }
        }
    )
    print("✅ Routers cadastrados.")

    async def upsert_database(name, module, entry_point):
        d = await prisma.databases.find_first(where={"name": name})
        data = {
            "name": name,
            "module": module,
            "entryPoint": entry_point,
            "active": True
        }
        if d:
            return await prisma.databases.update(where={"id": d.id}, data=data)
        return await prisma.databases.create(data=data)

    # NAME: "mongo"
    # MODULE: "database.mongo.mongodb"
    # ENTRYPOINT: "MongoDBConnection" (O nome da sua classe)
    await upsert_database("mongo", "database.mongo.mongodb", "MongoDBConnection")

    await prisma.disconnect()
    print("🏁 Seed finalizado com sucesso!")

if __name__ == "__main__":
    asyncio.run(run_seed())