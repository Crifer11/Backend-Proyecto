import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["SSE"])

# Diccionario de conexiones activas { id_vigilante: asyncio.Queue }
# Se usa una Queue por vigilante para poder empujar eventos desde /analizar
conexiones_activas: dict[int, asyncio.Queue] = {}


@router.get("/sse/{id_vigilante}")
async def sse(id_vigilante: int):
    """
    El front se conecta aquí al iniciar sesión.
    La conexión se mantiene abierta hasta que el vigilante cierre sesión.
    """
    queue = asyncio.Queue()
    conexiones_activas[id_vigilante] = queue

    async def stream():
        try:
            while True:
                # Espera hasta que haya un evento para este vigilante
                data = await queue.get()
                yield f"data: {json.dumps(data)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            # Limpiar conexión al cerrar sesión o caerse
            conexiones_activas.pop(id_vigilante, None)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # importante para Railway
        }
    )


async def empujar_evento(id_vigilante: int, data: dict):
    """
    Llamada desde /analizar para empujar resultado al front.
    Si el vigilante no está conectado por SSE, simplemente no hace nada.
    """
    queue = conexiones_activas.get(id_vigilante)
    if queue:
        await queue.put(data)
