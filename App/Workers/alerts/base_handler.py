from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta

class BaseAlertHandler(ABC):
    def __init__(self, worker):
        self.worker = worker # Acesso ao db, prisma, etc.

    @staticmethod
    def now_utc() -> datetime:
        """
        Retorna o datetime atual explicitly em UTC (+00:00).
        Garante que a comparação bata exatamente com o formato armazenado no MongoDB.
        """
        return datetime.now(timezone.utc)

    @staticmethod
    def minutes_ago(minutes: int) -> datetime:
        """Retorna o exato momento de N minutos atrás, com o fuso UTC aplicado."""
        return BaseAlertHandler.now_utc() - timedelta(minutes=minutes)

    @property
    @abstractmethod
    def cooldown_minutes(self) -> int:
        pass

    @abstractmethod
    async def verify(self, condition: dict) -> tuple[bool, dict | list]:
        """Retorna (condição_atendida, contexto)"""
        pass

    @abstractmethod
    def get_notification_payload(self, manager_name: str, replace_dict: dict) -> tuple[str, list]:
        """Retorna (template_name, template_params)"""
        pass