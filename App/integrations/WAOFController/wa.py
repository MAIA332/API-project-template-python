import os
import aiohttp

class WAOFController():
    def __init__(self):
        pass

    async def send(self, phone, template_name, template_params=None):
        print(f"\033[92m[WAOF] Preparando envio de template WhatsApp (mensagem ativa) para {phone}...\033[0m")
        
        token = os.getenv("META_TOKEN")
        url = os.getenv("META_URL")
        
        if not token or not url:
            print("\033[91m[ERRO] META_TOKEN ou META_URL não configurados no .env\033[0m")
            return

        # Limpeza do número de telefone (apenas dígitos)
        clean_phone = ''.join(filter(str.isdigit, phone))
        
        # Headers de autenticação da Meta
        headers = {
            "Authorization": f"{token}", 
            "Content-Type": "application/json"
        }

        # ---------------------------------------------------------------------
        # ENVIAR COMO TEMPLATE PAGO (Mensagem Ativa)
        # ---------------------------------------------------------------------
        lang_code = "pt_BR"
        components = []
        if template_params:
            components.append({
                "type": "body",
                "parameters": template_params
            })

        body_template = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_phone, 
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": lang_code
                }
            }
        }
        
        if components:
            body_template["template"]["components"] = components

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=body_template, headers=headers) as response:
                    result = await response.json()
                    
                    if response.status in [200, 201]:
                        msg_id = result.get('messages', [{}])[0].get('id')
                        print(f"\033[92m[SUCESSO] Template '{template_name}' enviado com sucesso! ID: {msg_id}\033[0m")
                    else:
                        print(f"\033[91m[ERRO META API] Falha ao enviar template: {result}\033[0m")
        except Exception as e:
            print(f"\033[91m[ERRO CÓDIGO] Exceção no Template: {e}\033[0m")