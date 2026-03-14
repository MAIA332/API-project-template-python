

import json, os
import aiohttp
import asyncio
import requests
import http.client
import urllib.parse
from .base_handler import BaseAlertHandler
import importlib
from prisma.models import AlertTypes

class AlertFactory:
    @staticmethod
    def get_handler(alert_type: AlertTypes, worker) -> BaseAlertHandler:
        handler_class = importlib.import_module(f"Workers.alerts.{alert_type.module}")
        handler_class = getattr(handler_class, alert_type.entryPoint)
        
        if not issubclass(handler_class, BaseAlertHandler):
            raise ValueError(f"Tipo de alerta desconhecido: {alert_type}")
        
        if not handler_class:
            raise ValueError(f"Tipo de alerta desconhecido: {alert_type}")
        
        return handler_class(worker)