from .base_handler import BaseAlertHandler

class TestAlertHandler(BaseAlertHandler):
    def __init__(self, worker):
        self.worker = worker

    @property
    def cooldown_minutes(self):
        # Mantém 15 minutos para não repetir o alerta instantaneamente
        return 15  
    
    async def verify(self, condition: dict):
        return (True, {})
    
    async def get_notification_payload(self, manager_name: str, replace_dict: dict):
        return ("test", [])