import os
from twilio.rest import Client

client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)

TWILIO_PHONE = os.getenv("TWILIO_PHONE")

def enviar_sms(numero, mensaje):
    numero = normalizar_celular_mx(numero)
    client.messages.create(
        to=numero,
        from_=TWILIO_PHONE,
        body=mensaje
    )

def hacer_llamada(celular: str, mensaje: str):
    celular = normalizar_celular_mx(celular)

    llamada = client.calls.create(
        to=celular,
        from_=TWILIO_PHONE,
        twiml=f'<Response><Say language="es-MX">{mensaje}</Say></Response>'
    )

    return llamada.sid


def normalizar_celular_mx(celular: str) -> str:
    celular = str(celular)  
    celular = celular.strip().replace(" ", "").replace("-", "")
    
    if celular.startswith("+"):
        return celular

    if len(celular) == 10:
        return "+52" + celular

    raise ValueError("Número de celular inválido")
