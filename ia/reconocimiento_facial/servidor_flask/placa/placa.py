import cv2
import torch
import pytesseract
import numpy as np
from huggingface_hub import hf_hub_download

# =========================
# Cargar modelo YOLO UNA SOLA VEZ
# =========================
print("Descargando modelo YOLOv5 de placas desde Hugging Face...")
model_path = hf_hub_download(
    repo_id="keremberke/yolov5m-license-plate",
    filename="best.pt"
)
print(f"Modelo descargado en: {model_path}")
modelo = torch.hub.load(
    "ultralytics/yolov5",
    "custom",
    path=model_path,
    force_reload=False,
    trust_repo=True
)
modelo.conf = 0.3
modelo.iou  = 0.45
print("Modelo de placas cargado correctamente")

# =========================
# Preprocesamiento
# =========================
def preprocesar_placa(img):
    h, w = img.shape[:2]

    # Recortar solo la franja central donde está el texto principal
    # Las placas mexicanas tienen logos arriba y "JALISCO/MEXICO" abajo
    # El texto principal ocupa aproximadamente el 30%-75% vertical
    margen_top    = int(h * 0.28)
    margen_bottom = int(h * 0.72)
    img = img[margen_top:margen_bottom, :]

    # Escalar para que Tesseract trabaje mejor (mínimo 400px de ancho)
    h2, w2 = img.shape[:2]
    if w2 < 400:
        scale = 400 / w2
        img = cv2.resize(img, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    # Convertir a gris
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Aumentar contraste con CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gris = clahe.apply(gris)

    # Suavizar ruido
    gris = cv2.GaussianBlur(gris, (3, 3), 0)

    # Umbralización de Otsu — mejor que adaptive para texto de alto contraste
    _, binaria = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Morfología para limpiar ruido
    kernel = np.ones((2, 2), np.uint8)
    procesada = cv2.morphologyEx(binaria, cv2.MORPH_CLOSE, kernel)

    return procesada

# =========================
# OCR con múltiples configuraciones
# =========================
def ocr_placa(img):
    resultados = []

    configs = [
        "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    ]

    for config in configs:
        texto = pytesseract.image_to_string(img, config=config)
        texto = texto.strip().replace(" ", "").replace("-", "").replace("\n", "")
        if texto:
            resultados.append(texto)

    if not resultados:
        return ""

    # Devolver el resultado más largo (generalmente el más completo)
    return max(resultados, key=len)

# =========================
# FUNCIÓN PRINCIPAL
# =========================
def reconocer_placa(imagen_bgr):
    """
    imagen_bgr: numpy array en formato BGR
    return: texto de la placa detectada o "" si no se detectó
    """
    if imagen_bgr is None:
        return ""

    resultados = modelo(imagen_bgr, size=640)
    detecciones = resultados.xyxy[0]

    print(f"Detecciones YOLO: {len(detecciones)}")

    if len(detecciones) == 0:
        return ""

    mejor = detecciones[detecciones[:, 4].argmax()]
    confianza = float(mejor[4])
    print(f"Confianza detección: {confianza:.2f}")

    x1, y1, x2, y2 = map(int, mejor[:4])

    # Margen al recorte
    margen = 5
    h, w = imagen_bgr.shape[:2]
    x1 = max(0, x1 - margen)
    y1 = max(0, y1 - margen)
    x2 = min(w, x2 + margen)
    y2 = min(h, y2 + margen)

    recorte = imagen_bgr[y1:y2, x1:x2]

    if recorte.size == 0:
        return ""

    procesada = preprocesar_placa(recorte)
    texto = ocr_placa(procesada)

    print(f"Placa detectada: '{texto}'")
    return texto
