import httpx
from typing import Dict, Any, Optional
import uuid

class APIClient:
    def __init__(self, base_url: str = "http://localhost:8003"): # Ajustado para a porta 8003 (Gateway/Backend)
        self.base_url = base_url
        self.token = None # Aqui guardaremos o JWT para requisições autenticadas
        
    def _get_headers(self):
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        # Futuramente: Adicionar headers de criptografia (ex: X-Public-Key)
        return headers

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None):
        request_headers = self._get_headers()
        if headers:
            request_headers.update(headers)
            
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}{endpoint}"
            return await client.get(url, params=params, headers=request_headers)

    async def post(self, endpoint: str, payload: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None):
        request_headers = self._get_headers()
        if headers:
            request_headers.update(headers)
            
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}{endpoint}"
            return await client.post(url, json=payload or {}, headers=request_headers)

    async def put(self, endpoint: str, payload: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None):
        request_headers = self._get_headers()
        if headers:
            request_headers.update(headers)
            
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}{endpoint}"
            return await client.put(url, json=payload or {}, headers=request_headers)

    async def patch(self, endpoint: str, payload: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None):
        request_headers = self._get_headers()
        if headers:
            request_headers.update(headers)
            
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}{endpoint}"
            return await client.patch(url, json=payload or {}, headers=request_headers)

    async def delete(self, endpoint: str, headers: Optional[Dict[str, str]] = None):
        request_headers = self._get_headers()
        if headers:
            request_headers.update(headers)
            
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}{endpoint}"
            return await client.delete(url, headers=request_headers)