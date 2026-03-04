from fastapi import APIRouter, Form
from database import conectar_db
from datetime import datetime

router = APIRouter()

@router.post("/registrar_incidente")
def registrar_incidente(
    titulo: str = Form(...),
    contenido: str = Form(...),
    nombre_v: str = Form(...),
    caseta: str = Form(...)
):
    try:
        conn = conectar_db()  # Usamos la conexión local
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO mini (fecha, titulo, contenido, nombre_v, caseta)
                VALUES (%s, %s, %s, %s, %s)
            """, (datetime.now(), titulo, contenido, nombre_v, caseta))
            conn.commit()
        conn.close()
        return {"mensaje": "✅ Incidente registrado correctamente"}
    except Exception as e:
        return {"error": f"❌ Error al registrar el incidente: {str(e)}"}
