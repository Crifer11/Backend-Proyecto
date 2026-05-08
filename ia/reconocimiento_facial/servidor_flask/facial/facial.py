import os
import cv2
import numpy as np
from deepface import DeepFace

# =========================
# Configuración
# =========================
carpeta_base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
carpeta_rostros = os.path.join(carpeta_base, 'static', 'perfiles')

MODELO     = "ArcFace"       # modelo más preciso de DeepFace
DETECTOR   = "retinaface"    # detector de rostros más preciso
DISTANCIA  = "cosine"        # métrica de distancia
TOLERANCIA = 0.40            # umbral para cosine con ArcFace (recomendado)

print(f"DeepFace configurado — modelo: {MODELO}, detector: {DETECTOR}")

# =========================
# Obtener fotos registradas
# =========================
def obtener_fotos_registradas():
    fotos = []
    if not os.path.exists(carpeta_rostros):
        print(f"⚠️ Carpeta de perfiles no encontrada: {carpeta_rostros}")
        return fotos

    for archivo in os.listdir(carpeta_rostros):
        if archivo.lower().endswith(('.png', '.jpg', '.jpeg')):
            try:
                id_persona = int(archivo.split('_')[0])
                ruta = os.path.join(carpeta_rostros, archivo)
                fotos.append((ruta, id_persona))
            except ValueError:
                continue

    print(f"Fotos de perfiles encontradas: {len(fotos)}")
    return fotos

# =========================
# Reconocimiento con DeepFace
# =========================
def reconocer_rostro_desde_imagen(imagen_rgb):
    """
    imagen_rgb: numpy array en formato RGB
    return: id_persona (int) o 0 si no hay match
    """
    fotos = obtener_fotos_registradas()

    if not fotos:
        print("⚠️ No hay fotos registradas en perfiles")
        return 0

    # Convertir RGB a BGR para DeepFace
    imagen_bgr = cv2.cvtColor(imagen_rgb, cv2.COLOR_RGB2BGR)

    mejor_distancia = float('inf')
    mejor_id        = 0

    for ruta, id_persona in fotos:
        try:
            resultado = DeepFace.verify(
                img1_path        = imagen_bgr,
                img2_path        = ruta,
                model_name       = MODELO,
                detector_backend = DETECTOR,
                distance_metric  = DISTANCIA,
                enforce_detection = False
            )

            distancia = resultado["distance"]
            print(f"ID {id_persona} — distancia: {distancia:.4f}")

            if distancia < mejor_distancia:
                mejor_distancia = distancia
                mejor_id        = id_persona

        except Exception as e:
            print(f"⚠️ Error comparando con ID {id_persona}: {e}")
            continue

    print(f"Mejor distancia: {mejor_distancia:.4f} (tolerancia: {TOLERANCIA})")

    if mejor_distancia <= TOLERANCIA:
        print(f"✅ Persona reconocida: ID {mejor_id} (distancia: {mejor_distancia:.4f})")
        return mejor_id

    print(f"❌ Persona no reconocida (distancia: {mejor_distancia:.4f})")
    return 0

# =========================
# Recarga dinámica de un rostro
# =========================
def recargar_rostro(ruta_imagen: str, id_persona: int):
    """
    Con DeepFace no hay encodings precargados —
    las fotos se leen directamente al momento de comparar.
    Esta función solo verifica que la foto existe y es válida.
    """
    try:
        if not os.path.exists(ruta_imagen):
            print(f"⚠️ Archivo no encontrado: {ruta_imagen}")
            return False

        DeepFace.extract_faces(
            img_path         = ruta_imagen,
            detector_backend = DETECTOR,
            enforce_detection = False
        )

        print(f"✅ Foto de perfil válida: ID {id_persona}")
        return True

    except Exception as e:
        print(f"❌ Error al verificar foto de perfil {id_persona}: {e}")
        return False
