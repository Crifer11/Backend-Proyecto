from fastapi import APIRouter, Form, HTTPException
from database import conectar_db
import secrets
from datetime import datetime, timedelta
from pydantic import BaseModel
from routers.twiliox import enviar_sms

router = APIRouter()

@router.post("/generar_token")
def generar_token(id: int = Form(...)):
    try:
        token = secrets.token_hex(8)
        expiracion = datetime.now() + timedelta(minutes=20)

        conn = conectar_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT celular FROM residente 
            WHERE id = %s
        """,(id,))
        
        res = cursor.fetchone()
        celular = res[0]
        
        cursor.execute("""
            UPDATE login SET token = %s, token_expira_en = %s
            WHERE id = %s
        """, (token, expiracion, id))
        conn.commit()
        cursor.close()
        conn.close()

        mensaje = f"Tu token es: {token}. No lo compartas con nadie. Valido por 20 minutos."
        enviar_sms(celular, mensaje)

        return {"mensaje": "Token generado correctamente", "token": token}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar token: {e}")


class TokenInput(BaseModel):
    id_usuario: int

class TokenRequest(BaseModel):
    token: str

@router.post("/verificar_token/")
def verificar_token(id_usuario: int, data: TokenRequest):
    print("✅ Data recibida:", data)
    print("✅ Token:", data.token)
    conn = conectar_db()
    cur = conn.cursor()
    token = data.token
    cur.execute("""
        SELECT token, token_expira_en FROM login WHERE id = %s
    """, (id_usuario,))
    resultado = cur.fetchone()
    if not resultado:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    token_bd, expira_en = resultado
    if token != token_bd or not token_bd:
        raise HTTPException(status_code=400, detail="Token inválido")
    
    if datetime.now() > expira_en:
        raise HTTPException(status_code=400, detail="El token ha expirado")
    
    # Invalidamos el token
    cur.execute("""
        UPDATE login SET token = NULL, token_expira_en = NULL WHERE id = %s
    """, (id_usuario,))
    conn.commit()
    return {"mensaje": "Token válido"}

