import os
import time
import face_recognition 
import cv2
from concurrent.futures import ThreadPoolExecutor, as_completed

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

        # Reducir resolución
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
# Comparar bloque
# =========================
def comparar_bloque(codigos_bloque, nombres_bloque, codificacion_objetivo):
    for idx, cod in enumerate(codigos_bloque):
        if face_recognition.compare_faces(
            [cod],
            codificacion_objetivo,
            tolerance=TOLERANCIA
        )[0]:
            return nombres_bloque[idx]
    return None

# =========================
# Reconocimiento EN MEMORIA
# =========================
def reconocer_rostro_desde_imagen(imagen_rgb):
    """
    imagen_rgb: numpy array en formato RGB
    return: id_persona o 0 si no hay match
    """
    inicio = time.time()

    # Reducir resolución
    imagen_rgb = cv2.resize(imagen_rgb, (0, 0), fx=0.5, fy=0.5)

    codificaciones = face_recognition.face_encodings(imagen_rgb, model='cnn')

    if not codificaciones:
        return 0

    codificacion_recibida = codificaciones[0]

    # =========================
    # Paralelismo
    # =========================
    num_hilos = min(os.cpu_count() or 4, len(CODIFICACIONES_REGISTRADAS))

    if num_hilos <= 1:
        for idx, cod in enumerate(CODIFICACIONES_REGISTRADAS):
            if face_recognition.compare_faces(
                [cod],
                codificacion_recibida,
                tolerance=TOLERANCIA
            )[0]:
                return NOMBRES_REGISTRADOS[idx]
        return 0

    bloque_size = len(CODIFICACIONES_REGISTRADAS) // num_hilos
    bloques = []
    nombres_bloques = []

    for i in range(num_hilos):
        start = i * bloque_size
        end = (i + 1) * bloque_size if i < num_hilos - 1 else len(CODIFICACIONES_REGISTRADAS)
        bloques.append(CODIFICACIONES_REGISTRADAS[start:end])
        nombres_bloques.append(NOMBRES_REGISTRADOS[start:end])

    with ThreadPoolExecutor(max_workers=num_hilos) as executor:
        futures = [
            executor.submit(comparar_bloque, cods, nombres, codificacion_recibida)
            for cods, nombres in zip(bloques, nombres_bloques)
        ]

        for future in as_completed(futures):
            resultado = future.result()
            if resultado is not None:
                return resultado

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

        # Si ya existe ese ID, reemplazar su encoding
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
