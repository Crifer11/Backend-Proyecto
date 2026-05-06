from fastapi import APIRouter, UploadFile, File, Form
import os
import base64
import json
import numpy as np 
import cv2
from ia.reconocimiento_facial.servidor_flask.facial.facial import reconocer_rostro_desde_imagen
from ia.reconocimiento_facial.servidor_flask.placa.placa import reconocer_placa, comparar_placa
from routers.administrar import guardar_imagen_jpg
from routers.twiliox import hacer_llamada
from routers.sse import empujar_evento
from database import conectar_db

router = APIRouter(prefix="/supervision", tags=["Supervisión"])

@router.post("/analizar")
async def analizar(
    serie: str = Form(...),
    id_vigilante: int = Form(...),
    img_rostro: UploadFile = File(...),
    img_placa: UploadFile = File(...)
):
    conn = conectar_db()
    cur = conn.cursor()
    
    # 1) Buscar auto por serie del tag
    cur.execute("SELECT id, placa FROM autos WHERE serie = %s", (serie,))
    auto = cur.fetchone()
    
    if not auto:
        # Notificar al front que el tag no está registrado
        await empujar_evento(id_vigilante, {
            "resultado": "Tag no registrado",
            "tipo": "alerta",
            "img_rostro": None,
            "img_placa": None,
            "id_reporte": None
        })
        return {"resultado": "Tag no registrado"}

    auto_id, placa_reg = auto
    
    contenido = await img_rostro.read()

    np_img = np.frombuffer(contenido, np.uint8)
    imagen_bgr = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
 
    if imagen_bgr is not None:
        imagen_rgb = cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2RGB)
        persona_detectada = reconocer_rostro_desde_imagen(imagen_rgb)

    bytes_placa = await img_placa.read()

    img_placa_cv = cv2.imdecode(
        np.frombuffer(bytes_placa, np.uint8),
        cv2.IMREAD_COLOR
    ) 

    if img_placa_cv is None:
        return {"error": "Imagen de placa inválida"}

    # 2) Reconocimiento de placa con IA
    placa_detectada = reconocer_placa(img_placa_cv)

    # 3) Convertir imágenes a base64 para mandarlas al front por SSE
    img_rostro_b64 = base64.b64encode(contenido).decode("utf-8")
    img_placa_b64 = base64.b64encode(bytes_placa).decode("utf-8")

    # 4) Obtener autorizados
    cur.execute("SELECT id_residente FROM residente_auto WHERE id_tag = %s", (auto_id,))
    autorizados = [row[0] for row in cur.fetchall()]
    
    print("PLACA DB:", placa_reg)
    print("PLACA IA:", placa_detectada)
    print("IGUALES:", placa_detectada == placa_reg)
    
    if persona_detectada not in autorizados or not comparar_placa(placa_detectada, placa_reg):
        
        if persona_detectada not in autorizados and placa_detectada != placa_reg:
            resultado = "Persona no autorizada y placa incorrecta"
    
        elif persona_detectada not in autorizados:
            resultado = "Persona no autorizada"
    
        elif not comparar_placa(placa_detectada, placa_reg):
            resultado = "Placa incorrecta"
            
        # --------- GENERAR REPORTE --------- 

        # 1) Obtener info del auto 
        cur.execute("""
            SELECT modelo, id_titular
            FROM autos
            WHERE id = %s
        """, (auto_id,))
        modelo_auto, id_titular = cur.fetchone()
    
        # 2) Obtener nombre del dueño
        cur.execute("""
            SELECT nombre, celular
            FROM residente
            WHERE id = %s
        """, (id_titular,))
        consulta = cur.fetchone()
        
        nombre_dueno, celular = consulta
        
        # Obtener vigilante y caseta
        cur.execute("""
            SELECT nombre, id_caseta
            FROM vigilante
            WHERE id = %s
        """, (id_vigilante,))
        nombre_vigilante, id_caseta = cur.fetchone()
        
        cur.execute("""
            SELECT ubicación
            FROM caseta
            WHERE id = %s
        """, (id_caseta,))
        nombre_caseta = cur.fetchone()[0]
        
        # 3) Conductor
        if persona_detectada == 0:
            conductor = "Desconocido"
        else:
            cur.execute("""
                SELECT nombre
                FROM residente
                WHERE id = %s
            """, (persona_detectada,))
            res = cur.fetchone()
            conductor = res[0] if res else "Desconocido"
    
        # 4) Motivo
        if persona_detectada not in autorizados and placa_detectada != placa_reg:
            motivo = "fallo en reconocimiento facial y de placas"
        elif persona_detectada not in autorizados:
            motivo = "fallo en reconocimiento facial"
        else:
            motivo = "fallo en reconocimiento de placas"
    
        # 5) Insertar reporte
        cur.execute("""
            INSERT INTO reporte
            (conductor, placa, caseta, vigilante, motivo, carro, dueño, texto_placa, id_residente)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING tiempo
        """, (
            conductor,
            placa_reg,
            nombre_caseta,        
            nombre_vigilante,
            motivo,
            modelo_auto,
            nombre_dueno,
            placa_detectada,
            id_titular
        ))
        id_reporte = cur.fetchone()[0]
        conn.commit()
        
        RUTA_REPORTES = "static/reportes"
        os.makedirs(RUTA_REPORTES, exist_ok=True)
        id_reportes = str(id_reporte).replace(":", "")
        
        ruta_rostro = f"{RUTA_REPORTES}/{id_reportes}_rostro.jpg"
        guardar_imagen_jpg(contenido, ruta_rostro)
            
        ruta_placa = f"{RUTA_REPORTES}/{id_reportes}_placa.jpg"
        guardar_imagen_jpg(bytes_placa, ruta_placa)

        img_rostro.file.close()

        mensaje = (
            f"ALERTA DE SEGURIDAD.\n"
            f"Vehículo {modelo_auto}, placa {placa_reg}, "
            f"detectado en evento irregular en {nombre_caseta}.\n"
            f"Motivo: {motivo}.\n"
            f"Contacte inmediato con administración."
        )

        try:
            hacer_llamada(celular, mensaje)
        except Exception as e:
            print("Error al realizar la llamada:", e)

        # 6) Empujar alerta al front por SSE
        await empujar_evento(id_vigilante, {
            "resultado": resultado,
            "tipo": "alerta",
            "img_rostro": img_rostro_b64,
            "img_placa": img_placa_b64,
            "id_reporte": str(id_reporte)
        })

        # 7) Responder al Python caseta (para el Arduino)
        return {"resultado": resultado}

    # --- AUTORIZADO ---

    # Empujar autorizado al front por SSE (con fotos para que el vigilante las vea)
    await empujar_evento(id_vigilante, {
        "resultado": "Autorizado",
        "tipo": "autorizado",
        "img_rostro": img_rostro_b64,
        "img_placa": img_placa_b64,
        "id_reporte": None
    })

    # Responder al Python caseta (para el Arduino)
    return {"resultado": "Autorizado"}


@router.post("/agregar_comentario")
async def agregar_comentario(
    tiempo: str = Form(...),
    comentario: str = Form(...)
):
    conn = conectar_db()
    cur = conn.cursor()

    print("Id reporte: ", tiempo)
    cur.execute(
        """
        UPDATE reporte
        SET descripción = %s
        WHERE tiempo = %s
        """,
        (comentario, tiempo)
    )

    conn.commit()
    cur.close()
    conn.close()

    return {"mensaje": "Comentario agregado correctamente"}
