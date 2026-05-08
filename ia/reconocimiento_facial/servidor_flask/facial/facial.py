import os
import time
import numpy as np
import face_recognition
import cv2

# =========================
# Precargar encodings al inicio
# =========================
carpeta_base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
carpeta_rostros = os.path.join(carpeta_base, 'static', 'perfiles')

CODIFICACIONES_REGISTRADAS = []
NOMBRES_REGISTRADOS = []

print("Cargando rostros registrados en memoria...")

for archivo in os.listdir(carpeta_rostros):
    if archivo.lower().endswith(('.png', '.jpg', '.jpeg')):
        ruta_imagen = os.path.join(carpeta_rostros, archivo)
        imagen = face_recognition.load_image_file(ruta_imagen)

        # Reducir resolución para acelerar
        imagen = cv2.resize(imagen, (0, 0), fx=0.5, fy=0.5)

        codificaciones = face_recognition.face_encodings(imagen, model='cnn')
        if codificaciones:
            CODIFICACIONES_REGISTRADAS.append(codificaciones[0])
            id_persona = int(archivo.split('_')[0])
            NOMBRES_REGISTRADOS.append(id_persona)
            print(f"Rostro cargado: {archivo}")

print(f"Total rostros cargados en memoria: {len(NOMBRES_REGISTRADOS)}")

# =========================
# Configuración
# =========================
TOLERANCIA = 0.45

# =========================
# Reconocimiento EN MEMORIA — mejor match
# =========================
def reconocer_rostro_desde_imagen(imagen_rgb):
    """
    imagen_rgb: numpy array en formato RGB
    return: id_persona (int) o 0 si no hay match
    """
    inicio = time.time()

    if not CODIFICACIONES_REGISTRADAS:
        print("⚠️ No hay rostros registrados en memoria")
        return 0

    # Reducir resolución para acelerar
    imagen_rgb = cv2.resize(imagen_rgb, (0, 0), fx=0.5, fy=0.5)

    codificaciones = face_recognition.face_encodings(imagen_rgb, model='cnn')

    if not codificaciones:
        print("⚠️ No se detectó ningún rostro en la imagen")
        return 0

    codificacion_recibida = codificaciones[0]

    # Calcular distancia contra todos los registrados
    # y quedarse con el de menor distancia (mejor match)
    distancias = face_recognition.face_distance(
        CODIFICACIONES_REGISTRADAS,
        codificacion_recibida
    )

    indice_mejor = int(np.argmin(distancias))
    mejor_distancia = distancias[indice_mejor]

    print(f"Mejor distancia facial: {mejor_distancia:.4f} (tolerancia: {TOLERANCIA})")

    if mejor_distancia <= TOLERANCIA:
        id_reconocido = NOMBRES_REGISTRADOS[indice_mejor]
        print(f"✅ Persona reconocida: ID {id_reconocido} (distancia: {mejor_distancia:.4f})")
        return id_reconocido

    print(f"❌ Persona no reconocida (distancia: {mejor_distancia:.4f})")
    return 0

# =========================
# Recarga dinámica de un rostro
# =========================
def recargar_rostro(ruta_imagen: str, id_persona: int):
    """
    Carga un rostro nuevo (o actualizado) en memoria sin reiniciar.
    Si el id ya existe, reemplaza su encoding. Si no, lo agrega.
    """
    try:
        imagen = face_recognition.load_image_file(ruta_imagen)
        imagen = cv2.resize(imagen, (0, 0), fx=0.5, fy=0.5)
        codificaciones = face_recognition.face_encodings(imagen, model='cnn')

        if not codificaciones:
            print(f"⚠️ No se detectó rostro en: {ruta_imagen}")
            return False

        nueva_cod = codificaciones[0]

        if id_persona in NOMBRES_REGISTRADOS:
            idx = NOMBRES_REGISTRADOS.index(id_persona)
            CODIFICACIONES_REGISTRADAS[idx] = nueva_cod
            print(f"🔄 Rostro actualizado en memoria: ID {id_persona}")
        else:
            CODIFICACIONES_REGISTRADAS.append(nueva_cod)
            NOMBRES_REGISTRADOS.append(id_persona)
            print(f"✅ Rostro nuevo cargado en memoria: ID {id_persona}")

        return True

    except Exception as e:
        print(f"❌ Error al recargar rostro {id_persona}: {e}")
        return False
