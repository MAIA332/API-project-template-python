import os
import json
import cmd2
import asyncio
import argparse
import uuid
from prisma import Prisma
from apicli import APIClient

# Importa pwd apenas se estiver em um sistema Unix (Linux/macOS)
try:
    import pwd
except ImportError:
    pwd = None

# Resolve o caminho absoluto para a pasta 'App/API'
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
API_DIR = os.path.join(BASE_DIR, 'API')

class APIShell(cmd2.Cmd):
    intro = "\nBem-vindo ao Shell Interativo da API.\nDigite 'help' ou '?' para listar os comandos.\n"
    prompt = "(api-shell) "

    def __init__(self):
        super().__init__()
        self.dirs = {
            "services": os.path.join(API_DIR, "services"),
            "controllers": os.path.join(API_DIR, "controllers"),
            "routes": os.path.join(API_DIR, "routes")
        }
        for path in self.dirs.values():
            os.makedirs(path, exist_ok=True)
            self._fix_ownership(path) 
            
        self.api_client = APIClient(base_url="http://localhost:8000")
        
    # ----------------------------------------------------------------------
    # Comandos de Sistema (Limpar Tela)
    # ----------------------------------------------------------------------
    @cmd2.with_category("Sistema")
    def do_cls(self, args):
        """Limpa a tela do terminal."""
        os.system('cls' if os.name == 'nt' else 'clear')

    @cmd2.with_category("Sistema")
    def do_clear(self, args):
        """Limpa a tela do terminal."""
        self.do_cls(args)

    # ----------------------------------------------------------------------
    # Correção Automática de Permissões (Linux/Sudo)
    # ----------------------------------------------------------------------
    def _fix_ownership(self, path: str):
        if os.name == 'posix' and pwd and hasattr(os, 'geteuid') and os.geteuid() == 0:
            sudo_user = os.getenv('SUDO_USER')
            if sudo_user:
                try:
                    user_info = pwd.getpwnam(sudo_user)
                    os.chown(path, user_info.pw_uid, user_info.pw_gid)
                except Exception:
                    pass

    # ----------------------------------------------------------------------
    # Formatação e Paginação de Saída
    # ----------------------------------------------------------------------
    def _print_table_paginated(self, items):
        """Transforma uma lista de dicionários em uma tabela formatada e paginada."""
        if not items:
            self.poutput("\n[Vazio] Nenhum registro encontrado.")
            return

        # Filtra objetos e listas aninhadas para manter a tabela legível
        headers = [k for k, v in items[0].items() if not isinstance(v, (dict, list))]
        if not headers:
            headers = list(items[0].keys())

        # Calcula a largura ideal para cada coluna (com um limite máximo)
        col_widths = {h: len(h) for h in headers}
        for item in items:
            for h in headers:
                val_str = str(item.get(h, ''))
                if len(val_str) > col_widths[h]:
                    col_widths[h] = min(len(val_str), 35) # Limite de 35 caracteres por coluna

        # Monta as linhas da tabela
        lines = []
        header_line = " | ".join(h.upper().ljust(col_widths[h]) for h in headers)
        lines.append("=" * len(header_line))
        lines.append(header_line)
        lines.append("=" * len(header_line))

        for item in items:
            row = []
            for h in headers:
                val_str = str(item.get(h, ''))
                if len(val_str) > 35:
                    val_str = val_str[:32] + "..." # Trunca textos muito longos
                row.append(val_str.ljust(col_widths[h]))
            lines.append(" | ".join(row))
        
        lines.append("-" * len(header_line))
        table_output = "\n".join(lines)

        # O método ppaged cria um buffer interativo navegável por setas/enter
        self.ppaged(table_output)

    def _print_response(self, response):
        """Helper para formatar a saída da API de forma inteligente"""
        self.poutput(f"\nStatus HTTP: {response.status_code}")
        
        try:
            data = response.json()
            
            # 1. Se a resposta contiver uma lista de dados, monta a tabela interativa
            if isinstance(data.get("data"), list):
                self._print_table_paginated(data["data"])
                
                # Exibe resumo da paginação caso a API retorne metadados
                if "meta" in data:
                    meta = data["meta"]
                    self.poutput(f"\n📊 Paginação: Página {meta.get('current_page')} de {meta.get('total_pages')} | Total de registros: {meta.get('total')}")
            
            # 2. Se for um objeto simples ou uma resposta curta, usa o Pretty Print
            else:
                formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
                # Se o JSON for muito grande, joga para o paginador interativo
                if len(formatted_json.splitlines()) > 30:
                    self.ppaged(formatted_json)
                else:
                    self.poutput(formatted_json)
                    
        except Exception:
            # Fallback caso a API não retorne um JSON válido
            if len(response.text.splitlines()) > 30:
                self.ppaged(response.text)
            else:
                self.poutput(response.text)
            
    # ======================================================================
    # COMANDOS DE AUTENTICAÇÃO E USUÁRIOS
    # ======================================================================
    login_parser = cmd2.Cmd2ArgumentParser(description="Autentica um usuário e salva o token na sessão.")
    login_parser.add_argument('email', type=str, help="Email do usuário")
    login_parser.add_argument('password', type=str, help="Senha do usuário")

    @cmd2.with_argparser(login_parser)
    def do_login(self, args):
        asyncio.run(self._async_login(args.email, args.password))

    async def _async_login(self, email, password):
        self.poutput("🔑 Autenticando...")
        resp = await self.api_client.post("/auth/login", {"email": email, "password": password})
        self._print_response(resp)
        if resp.status_code in [200, 201]:
            data = resp.json()
            token = data.get("token") or data.get("access_token") or (data.get("data") and data["data"].get("token"))
            if token:
                self.api_client.token = token
                self.poutput("\n✅ Token salvo com sucesso! Você está autenticado nesta sessão.")

    @cmd2.with_category("Auth")
    def do_test_auth(self, args):
        """Testa se o token atual é válido na rota /auth/test/"""
        asyncio.run(self._async_test_auth())

    async def _async_test_auth(self):
        resp = await self.api_client.get("/auth/test/")
        self._print_response(resp)

    user_parser = cmd2.Cmd2ArgumentParser(description="Cria um novo usuário.")
    user_parser.add_argument('--name', required=True)
    user_parser.add_argument('--email', required=True)
    user_parser.add_argument('--password', required=True)
    user_parser.add_argument('--role', default="ADMIN")

    @cmd2.with_argparser(user_parser)
    def do_create_user(self, args):
        payload = {
            "name": args.name,
            "email": args.email,
            "password": args.password,
            "role_identifier": args.role,
            "description": "Criado via Shell"
        }
        asyncio.run(self._async_post("/users/", payload))

    # ======================================================================
    # MÉTODOS AUXILIARES DE REQUISIÇÃO (DRY)
    # ======================================================================
    async def _async_get(self, endpoint, params=None):
        resp = await self.api_client.get(endpoint, params)
        self._print_response(resp)

    async def _async_post(self, endpoint, payload, headers=None):
        kwargs = {}
        if headers:
            kwargs['headers'] = headers
            
        resp = await self.api_client.post(endpoint, payload, **kwargs)
        self._print_response(resp)

    async def _async_patch(self, endpoint, payload):
        resp = await self.api_client.patch(endpoint, payload)
        self._print_response(resp)

    async def _async_delete(self, endpoint):
        resp = await self.api_client.delete(endpoint)
        self._print_response(resp)

    # ----------------------------------------------------------------------
    # Comando 'generate' (Scaffold + Prisma)
    # ----------------------------------------------------------------------
    gen_parser = cmd2.Cmd2ArgumentParser(description="Gera CRUD, Parameters, Routes e registra no banco Prisma.")
    gen_parser.add_argument('module', type=str, help="Nome do Módulo (ex: User, Product, Category)")
    gen_parser.add_argument('-e', '--endpoint', type=str, help="Endpoint base (ex: /users). Se omitido, usa /module")

    @cmd2.with_argparser(gen_parser)
    def do_generate(self, args):
        """Gera um novo módulo completo para a API e mapeia no banco"""
        module_name = args.module.capitalize()
        endpoint = args.endpoint if args.endpoint else f"/{args.module.lower()}"
        
        self.poutput(f"\nIniciando geracao do modulo '{module_name}' com CRUD padrão...")
        
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._async_generate(module_name, endpoint))
        except RuntimeError:
            asyncio.run(self._async_generate(module_name, endpoint))

    async def _async_generate(self, name: str, endpoint: str):
        name_lower = name.lower()
        
        srv_file = f"{name_lower}_service"
        ctrl_file = f"{name_lower}_controller"
        router_file = f"{name_lower}_routes"
        
        srv_class = f"{name}Service"
        ctrl_class = f"{name}Controller"
        router_func = f"init_{name_lower}_router"

        # 1. Cria os arquivos físicos
        self._create_service_file(srv_file, srv_class, name_lower)
        self._create_controller_file(ctrl_file, ctrl_class, srv_class)
        self._create_router_file(router_file, router_func, name)

        self.poutput("[OK] Arquivos Python (CRUD) gerados com sucesso.")

        # 2. Registra tudo no Prisma
        self.poutput("Conectando ao banco de dados PostgreSQL...")
        prisma = Prisma()
        
        try:
            await prisma.connect()
            
            # --- SERVICE & PARAMETERS ---
            self.poutput(f" -> Registrando Service: {srv_class}")
            new_service = await prisma.services.create(
                data={
                    "name": srv_class,
                    "description": f"Servico CRUD principal do modulo {name}",
                    "module": srv_file,
                    "entryPoint": srv_class,
                    "active": True
                }
            )

            self.poutput(" -> Registrando Parameters padrões (skip, take, data, item_id)...")
            default_params = [
                {"name": "data", "description": "Payload JSON com os dados do recurso"},
                {"name": "item_id", "description": "ID único do recurso (UUID)"},
                {"name": "skip", "description": "Paginação: Número de registros para pular"},
                {"name": "take", "description": "Paginação: Limite de registros a retornar"}
            ]
            
            for param in default_params:
                await prisma.parameters.create(
                    data={
                        "name": param["name"],
                        "description": param["description"],
                        "Services": {"connect": [{"id": new_service.id}]}
                    }
                )

            # --- CONTROLLER ---
            self.poutput(f" -> Registrando Controller: {ctrl_class}")
            new_controller = await prisma.controllers.create(
                data={
                    "name": ctrl_class,
                    "description": f"Controller CRUD principal do modulo {name}",
                    "module": ctrl_file,
                    "entryPoint": ctrl_class,
                    "active": True,
                    "services": {"connect": [{"id": new_service.id}]}
                }
            )

            # --- ROUTER & ROUTES ---
            self.poutput(f" -> Registrando Router: {router_func} em {endpoint}")
            new_router = await prisma.routers.create(
                data={
                    "name": f"{name}Router",
                    "description": f"Rotas CRUD do modulo {name}",
                    "module": router_file,
                    "entryPoint": router_func,
                    "endpoint": endpoint,
                    "active": True,
                    "Controllers": {"connect": {"id": new_controller.id}}
                }
            )

            self.poutput(" -> Registrando endpoints (GET, POST, PUT, DELETE) na tabela Route...")
            
            # Cria as rotas exatas baseadas no arquivo CRUD gerado
            crud_routes = [
                {"path": endpoint, "method": "GET"},
                {"path": endpoint, "method": "POST"},
                {"path": f"{endpoint}/:id", "method": "GET"},
                {"path": f"{endpoint}/:id", "method": "PUT"},
                {"path": f"{endpoint}/:id", "method": "DELETE"}
            ]

            for route_data in crud_routes:
                await prisma.route.create(
                    data={
                        "path": route_data["path"],
                        "method": route_data["method"],
                        "Routers": {"connect": [{"id": new_router.id}]}
                    }
                )

            self.poutput("\n[SUCESSO] Modulo completo registrado no banco com sucesso!")

        except Exception as e:
            self.perror(f"[ERRO] Falha ao registrar no Prisma: {e}")
        finally:
            if prisma.is_connected():
                await prisma.disconnect()

    # ----------------------------------------------------------------------
    # Templates Aprimorados (CRUD Base)
    # ----------------------------------------------------------------------
    def _create_service_file(self, file_name, class_name, name_lower):
        path = os.path.join(self.dirs['services'], f"{file_name}.py")
        content = f"""from typing import Dict, Any, List

class {class_name}:
    def __init__(self, app, prisma, mongo=None, ws_server=None):
        self.app = app
        self.prisma = prisma
        self.mongo = mongo
        self.ws = ws_server
        self.name = "{class_name}"

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {{"success": True, "message": "Criado com sucesso", "data": data}}

    async def get_all(self, skip: int = 0, take: int = 20) -> Dict[str, Any]:
        return {{"success": True, "data": []}}

    async def get_by_id(self, item_id: str) -> Dict[str, Any]:
        return {{"success": True, "id": item_id}}

    async def update(self, item_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return {{"success": True, "message": "Atualizado com sucesso"}}

    async def delete(self, item_id: str) -> Dict[str, Any]:
        return {{"success": True, "message": "Deletado com sucesso"}}
"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self._fix_ownership(path)

    def _create_controller_file(self, file_name, class_name, srv_class):
        path = os.path.join(self.dirs['controllers'], f"{file_name}.py")
        content = f"""from typing import Dict, Any

class {class_name}:
    def __init__(self, {srv_class}):
        self.service = {srv_class}

    async def handle_create(self, data: Dict[str, Any]):
        try:
            return await self.service.create(data)
        except Exception as e:
            return {{"success": False, "error": str(e)}}

    async def handle_get_all(self, skip: int = 0, take: int = 20):
        try:
            skip = max(0, int(skip))
            take = max(1, min(100, int(take)))
            return await self.service.get_all(skip=skip, take=take)
        except Exception as e:
            return {{"success": False, "error": str(e)}}

    async def handle_get_by_id(self, item_id: str):
        try:
            return await self.service.get_by_id(item_id)
        except Exception as e:
            return {{"success": False, "error": str(e)}}

    async def handle_update(self, item_id: str, data: Dict[str, Any]):
        try:
            return await self.service.update(item_id, data)
        except Exception as e:
            return {{"success": False, "error": str(e)}}

    async def handle_delete(self, item_id: str):
        try:
            return await self.service.delete(item_id)
        except Exception as e:
            return {{"success": False, "error": str(e)}}
"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self._fix_ownership(path)

    def _create_router_file(self, file_name, func_name, tag_name):
        path = os.path.join(self.dirs['routes'], f"{file_name}.py")
        content = f"""from fastapi import APIRouter, Body, HTTPException, Query
from typing import Dict, Any

def {func_name}(controller) -> APIRouter:
    router = APIRouter(tags=["{tag_name}"])

    @router.post("")
    async def create(data: Dict[str, Any] = Body(...)):
        result = await controller.handle_create(data)
        if isinstance(result, dict) and not result.get("success", True):
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result

    @router.get("")
    async def get_all(
        skip: int = Query(0, description="Pular X registros"),
        take: int = Query(20, description="Pegar X registros")
    ):
        result = await controller.handle_get_all(skip=skip, take=take)
        if isinstance(result, dict) and not result.get("success", True):
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result

    @router.get("/{{item_id}}")
    async def get_by_id(item_id: str):
        result = await controller.handle_get_by_id(item_id)
        if not result or (isinstance(result, dict) and not result.get("success", True)):
            raise HTTPException(status_code=404, detail="Item não encontrado")
        return result

    @router.put("/{{item_id}}")
    async def update(item_id: str, data: Dict[str, Any] = Body(...)):
        result = await controller.handle_update(item_id, data)
        if isinstance(result, dict) and not result.get("success", True):
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result

    @router.delete("/{{item_id}}")
    async def delete(item_id: str):
        result = await controller.handle_delete(item_id)
        if isinstance(result, dict) and not result.get("success", True):
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result

    return router
"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self._fix_ownership(path)

if __name__ == '__main__':
    app = APIShell()
    app.cmdloop()