```
├─ .dockerignore
├─ App
│  ├─ API
│  │  ├─ controllers
│  │  │  └─ users.py
│  │  ├─ middlewares
│  │  │  └─ auth
│  │  │     ├─ authentication.py
│  │  │     └─ check_roles.py
│  │  ├─ routes
│  │  │  └─ users.py
│  │  └─ services
│  │     └─ users.py
│  ├─ bootstrap
│  │  └─ bootstrap_app.py
│  ├─ database
│  │  └─ prisma
│  │     └─ prisma.py
│  ├─ prisma
│  │  ├─ migrations
│  │  │  ├─ 20260221011109_init
│  │  │  │  └─ migration.sql
│  │  │  ├─ 20260221012551_add_controller_on_system_mapping
│  │  │  │  └─ migration.sql
│  │  │  └─ migration_lock.toml
│  │  └─ schema.prisma
│  ├─ server.py
│  └─ servers
│     └─ ws_server.py
├─ docker-compose.yml
├─ Dockerfile
```