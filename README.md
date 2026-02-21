# 🚀 FastAPI Dynamic Template - Sinapse Labs

Este é o template base para novos serviços e APIs (como o Cortex e SinaCloud). Ele utiliza uma arquitetura orientada a **Injeção de Dependência Dinâmica**, onde o carregamento de Rotas, Controllers e Services é ditado pelo Banco de Dados (PostgreSQL) durante o *startup* da aplicação.

## 🌟 Principais Tecnologias
* **FastAPI**: Framework web assíncrono e de alta performance.
* **Prisma ORM**: Tipagem forte e migrações seguras para o PostgreSQL.
* **Motor (MongoDB)**: Persistência assíncrona para logs e documentos não estruturados.
* **Uvicorn**: Servidor ASGI.
* **WebSockets**: Servidor WS nativo em background para real-time.
* **Docker**: Ambiente pronto para o Coolify / SinaCloud.

---

## 📂 Estrutura de Diretórios

A arquitetura segue o padrão de Camadas (Layered Architecture), separando responsabilidades de forma estrita:

```text
├─ .dockerignore
├─ App/
│  ├─ API/
│  │  ├─ controllers/     # Lógica de orquestração de rotas (recebe Services via injeção)
│  │  ├─ middlewares/     # Interceptadores (Auth, Validação de Roles)
│  │  ├─ routes/          # Definição de Endpoints (Pydantic Models de In/Out)
│  │  └─ services/        # Regras de Negócio e acesso ao Banco de Dados (Prisma/Mongo)
│  ├─ bootstrap/          
│  │  └─ bootstrap_app.py # Motor dinâmico de Injeção de Dependência
│  ├─ database/
│  │  ├─ prisma/          # Conexão Singleton do Prisma
│  │  └─ mongodb/         # Conexão Singleton do Motor (se aplicável)
│  ├─ prisma/             # Schema do banco de dados e Migrations
│  ├─ servers/
│  │  └─ ws_server.py     # Lógica do Servidor de WebSockets
│  └─ server.py           # Entrypoint da aplicação (Lifespan + Uvicorn)
├─ docker-compose.yml     # Serviços auxiliares (Postgres, Mongo, Redis)
├─ Dockerfile             # Setup de build da imagem final
└─ requirements.txt       # Dependências do Python
```