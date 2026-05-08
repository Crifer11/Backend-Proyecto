import os
import cv2
import numpy as np
from deepface import DeepFace
from deepface.modules import modeling
from deepface.commons import image_utils

# =========================
# Configuración
# =========================
carpeta_base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
carpeta_rostros = os.path.join(carpeta_base, 'static', 'perfiles')

MODELO     = "ArcFace"
DETECTOR   = "retinaface"
DISTANCIA  = "cosine"
TOLERANCIA = 0.40

# =========================
# Precargar embeddings al arrancar
# =========================
EMBEDDINGS_REGISTRADOS = []  # lista de (id_persona, embedding)

def _calcular_embedding(ruta_imagen):
    """Calcula el embedding de una imagen de perfil."""
    try:
        resultado = DeepFace.represent(
            img_path         = ruta_imagen,
            model_name       = MODELO,
            detector_backend = DETECTOR,
            enforce_detection = False
        )
        if resultado:
            return np.array(resultado[0]["embedding"])
    except Exception as e:
        print(f"⚠️ Error calculando embedding de {ruta_imagen}: {e}")
    return None

def cargar_embeddings():
    """Carga todos los embeddings de perfiles al arrancar."""
    global EMBEDDINGS_REGISTRADOS
    EMBEDDINGS_REGISTRADOS = []

    if not os.path.exists(carpeta_rostros):
        print(f"⚠️ Carpeta de perfiles no encontrada: {carpeta_rostros}")
        return

    print("Cargando embeddings de perfiles con ArcFace...")
    for archivo in os.listdir(carpeta_rostros):
        if archivo.lower().endswith(('.png', '.jpg', '.jpeg')):
            try:
                id_persona = int(archivo.split('_')[0])
                ruta = os.path.join(carpeta_rostros, archivo)
                embedding = _calcular_embedding(ruta)
                if embedding is not None:
                    EMBEDDINGS_REGISTRADOS.append((id_persona, embedding))
                    print(f"✅ Embedding cargado: ID {id_persona}")
            except ValueError:
                continue

    print(f"Total embeddings cargados: {len(EMBEDDINGS_REGISTRADOS)}")

# Cargar al importar el módulo
cargar_embeddings()

# =========================
# Distancia cosine
# =========================
def distancia_cosine(e1, e2):
    return 1 - np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2))

# =========================
# Reconocimiento con DeepFace
# =========================
def reconocer_rostro_desde_imagen(imagen_rgb):
    """
    imagen_rgb: numpy array en formato RGB
    return: id_persona (int) o 0 si no hay match
    """
    if not EMBEDDINGS_REGISTRADOS:
        print("⚠️ No hay embeddings registrados en memoria")
        return 0

    # Convertir RGB a BGR para DeepFace
    imagen_bgr = cv2.cvtColor(imagen_rgb, cv2.COLOR_RGB2BGR)

    # Calcular embedding de la imagen recibida
    try:
        resultado = DeepFace.represent(
            img_path         = imagen_bgr,
            model_name       = MODELO,
            detector_backend = DETECTOR,
            enforce_detection = False
        )
        if not resultado:
            print("⚠️ No se detectó rostro en la imagen")
            return 0
        embedding_recibido = np.array(resultado[0]["embedding"])
    except Exception as e:
        print(f"⚠️ Error procesando imagen: {e}")
        return 0

    # Comparar contra todos los embeddings precargados
    mejor_distancia = float('inf')
    mejor_id        = 0

    for id_persona, embedding in EMBEDDINGS_REGISTRADOS:
        distancia = distancia_cosine(embedding_recibido, embedding)
        print(f"ID {id_persona} — distancia: {distancia:.4f}")
        if distancia < mejor_distancia:
            mejor_distancia = distancia
            mejor_id        = id_persona

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
    Calcula y guarda el embedding del nuevo perfil en memoria
    sin necesidad de reiniciar el servidor.
    """
    try:
        embedding = _calcular_embedding(ruta_imagen)
        if embedding is None:
            print(f"⚠️ No se pudo calcular embedding para ID {id_persona}")
            return False

        # Si ya existe ese ID, reemplazar su embedding
        for i, (id_reg, _) in enumerate(EMBEDDINGS_REGISTRADOS):
            if id_reg == id_persona:
                EMBEDDINGS_REGISTRADOS[i] = (id_persona, embedding)
                print(f"🔄 Embedding actualizado en memoria: ID {id_persona}")
                return True

        # Si no existe, agregar
        EMBEDDINGS_REGISTRADOS.append((id_persona, embedding))
        print(f"✅ Embedding nuevo cargado en memoria: ID {id_persona}")
        return True

    except Exception as e:
        print(f"❌ Error al recargar rostro {id_persona}: {e}")
        return False
