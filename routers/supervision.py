from fastapi import APIRouter, UploadFile, File, Form
import os
import base64
import asyncio
import numpy as np 
import cv2
from ia.reconocimiento_facial.servidor_flask.facial.facial import reconocer_rostro_desde_imagen
from ia.reconocimiento_facial.servidor_flask.placa.placa import reconocer_placa, comparar_placa
from routers.administrar import guardar_imagen_jpg
from routers.twiliox import hacer_llamada
from routers.sse import empujar_evento
from database import conectar_db
import time

router = APIRouter(prefix="/supervision", tags=["Supervisión"])

# =========================
# Llamada con reintentos si no contesta
# Se ejecuta en segundo plano sin bloquear el servidor
# =========================
async def llamar_con_reintentos(celular: str, mensaje: str, intentos: int = 2, delay: int = 30):
    from twilio.rest import Client
    client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

    for i in range(intentos):
        try:
            sid = hacer_llamada(celular, mensaje)
            print(f"📞 Llamada {i+1} realizada, SID: {sid}")

            # Esperar sin bloquear el servidor
            await asyncio.sleep(delay)

            # Verificar estado de la llamada
            estado = client.calls(sid).fetch().status
            print(f"Estado llamada {i+1}: {estado}")

            if estado == "completed":
                print("✅ Llamada contestada, no se reintenta")
                break
            else:
                print(f"📵 No contestó ({estado}), reintentando...")

        except Exception as e:
            print(f"❌ Error en llamada {i+1}: {e}")

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
        t1 = time.time()
        persona_detectada = reconocer_rostro_desde_imagen(imagen_rgb)
        t2 = time.time()
        print(f"⏱️ Facial tardó: {t2-t1:.2f} segundos")
    
    bytes_placa = await img_placa.read()
    img_placa_cv = cv2.imdecode(
        np.frombuffer(bytes_placa, np.uint8),
        cv2.IMREAD_COLOR
    )
    
    if img_placa_cv is None:
        return {"error": "Imagen de placa inválida"}
    
    t3 = time.time()
    placa_detectada = reconocer_placa(img_placa_cv)
    t4 = time.time()
    print(f"⏱️ Placa tardó: {t4-t3:.2f} segundos")

    # 3) Convertir imágenes a base64 para mandarlas al front por SSE
    img_rostro_b64 = base64.b64encode(contenido).decode("utf-8")
    img_placa_b64 = base64.b64encode(bytes_placa).decode("utf-8")

    # 4) Obtener autorizados
    cur.execute("SELECT id_residente FROM residente_auto WHERE id_tag = %s", (auto_id,))
    autorizados = [row[0] for row in cur.fetchall()]
    
    # Calcular validaciones UNA SOLA VEZ con tolerancia
    persona_no_autorizada = persona_detectada not in autorizados
    placa_no_coincide     = not comparar_placa(placa_detectada, placa_reg)
    
    print("PLACA DB:", placa_reg)
    print("PLACA IA:", placa_detectada)
    print("PERSONA NO AUTORIZADA:", persona_no_autorizada)
    print("PLACA NO COINCIDE:", placa_no_coincide)
    
    if persona_no_autorizada or placa_no_coincide:
    
        if persona_no_autorizada and placa_no_coincide:
            resultado = "Persona no autorizada y placa incorrecta"
            motivo = "fallo en reconocimiento facial y de placas"
        elif persona_no_autorizada:
            resultado = "Persona no autorizada"
            motivo = "fallo en reconocimiento facial"
        else:
            resultado = "Placa incorrecta"
            motivo = "fallo en reconocimiento de placas"
            
        # --------- GENERAR REPORTE --------- 

        cur.execute("""
            SELECT modelo, id_titular
            FROM autos
            WHERE id = %s
        """, (auto_id,))
        modelo_auto, id_titular = cur.fetchone()
    
        cur.execute("""
            SELECT nombre, celular
            FROM residente
            WHERE id = %s
        """, (id_titular,))
        consulta = cur.fetchone()
        
        nombre_dueno, celular = consulta
        
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

        # Llamada con reintentos en segundo plano — no bloquea el servidor
        asyncio.create_task(llamar_con_reintentos(celular, mensaje, intentos=2, delay=30))

        await empujar_evento(id_vigilante, {
            "resultado": resultado,
            "tipo": "alerta",
            "img_rostro": img_rostro_b64,
            "img_placa": img_placa_b64,
            "id_reporte": str(id_reporte)
        })

        return {"resultado": resultado}

    # --- AUTORIZADO ---
    await empujar_evento(id_vigilante, {
        "resultado": "Autorizado",
        "tipo": "autorizado",
        "img_rostro": img_rostro_b64,
        "img_placa": img_placa_b64,
        "id_reporte": None
    })

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
