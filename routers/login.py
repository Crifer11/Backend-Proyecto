from fastapi import APIRouter, HTTPException, Form
from database import conectar_db  # Asegúrate de tener ambas si las usas
from pydantic import BaseModel

router = APIRouter()

# Ruta para iniciar sesión
@router.post("/login")
def login(id: int = Form(...), contrasena: str = Form(...)):
    try:
        conn = conectar_db()
        cur = conn.cursor()
        cur.execute("SELECT rol FROM login WHERE id = %s AND contraseña = %s", (id, contrasena))
        resultado = cur.fetchone()
        cur.close()
        conn.close()

        if resultado:
            rol = resultado[0]
            return {"mensaje": "✅ Login exitoso", "id": id, "rol": rol}
        else:
            raise HTTPException(status_code=401, detail="❌ ID o contraseña incorrectos")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error del servidor: {e}")


@router.get("/obtener_nombre")
def obtener_nombre(id: int, rol: str):
    try:
        conn = conectar_db()  # Conexión local
        with conn.cursor() as cursor:
            if rol == "Vigilante":
                cursor.execute("""
                    SELECT v.nombre, c.ubicación 
                    FROM vigilante v
                    JOIN caseta c ON v.id_caseta = c.id
                    WHERE v.id = %s
                """, (id,))
                resultado = cursor.fetchone()
                if resultado:
                    return {"nombre": resultado[0], "caseta": resultado[1]}
                else:
                    return {"error": "Vigilante no encontrado"}

            elif rol == "Residente" or "Autorizado":
                cursor.execute("SELECT nombre FROM residente WHERE id = %s", (id,))
                resultado = cursor.fetchone()

            elif rol == "Administrador":
                cursor.execute("SELECT nombre FROM administrador WHERE id = %s", (id,))
                resultado = cursor.fetchone()

            else:
                return {"error": "Rol no válido"}

        conn.close()

        if resultado:
            return {"nombre": resultado[0]}
        else:
            return {"error": "Usuario no encontrado"}

    except Exception as e:
        return {"error": f"❌ Error al obtener el nombre: {str(e)}"}


class NuevaContrasenaInput(BaseModel):
    id_usuario: int
    nueva_contrasena: str

@router.post("/cambiar_contrasena")
def cambiar_contrasena(data: NuevaContrasenaInput):
    try:
        conn = conectar_db()
        cursor = conn.cursor()

        # Actualizar contraseña
        cursor.execute("""
            UPDATE login
            SET contraseña = %s
            WHERE id = %s
        """, (data.nueva_contrasena, data.id_usuario))

        conn.commit()
        cursor.close()
        conn.close()

        return {"mensaje": "✅ Contraseña actualizada correctamente"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error al cambiar la contraseña: {e}")