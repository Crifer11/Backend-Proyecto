import asyncio
import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["SSE"])

# Diccionario de conexiones activas { id_vigilante: asyncio.Queue }
conexiones_activas: dict[int, asyncio.Queue] = {}


@router.get("/sse/{id_vigilante}")
async def sse(id_vigilante: int, request: Request):
    """
    El front se conecta aquí al iniciar sesión.
    La conexión se mantiene abierta hasta que el vigilante cierre sesión.
    """
    queue = asyncio.Queue()
    conexiones_activas[id_vigilante] = queue

    async def stream():
        try:
            while True:
                # Verificar si el cliente sigue conectado
                if await request.is_disconnected():
                    break

                try:
                    # Esperar evento con timeout de 25 segundos
                    # Si no hay evento, mandar un comentario keepalive
                    # para que Railway no cierre la conexión por inactividad
                    data = await asyncio.wait_for(queue.get(), timeout=25)
                    yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    # Keepalive — Railway cierra conexiones inactivas
                    yield ": keepalive\n\n"

        except asyncio.CancelledError:
            pass
        finally:
            conexiones_activas.pop(id_vigilante, None)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream; charset=utf-8",
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
