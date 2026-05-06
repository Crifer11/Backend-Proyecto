import cv2
import torch
import easyocr
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
# Cargar EasyOCR UNA SOLA VEZ
# =========================
print("Cargando EasyOCR...")
lector = easyocr.Reader(['en'], gpu=False)
print("EasyOCR cargado correctamente")

# =========================
# Preprocesamiento
# =========================
def preprocesar_placa(img):
    h, w = img.shape[:2]

    # Recortar solo la franja del texto principal
    # Las placas mexicanas tienen logos arriba y JALISCO/MEXICO abajo
    margen_top    = int(h * 0.28)
    margen_bottom = int(h * 0.72)
    img = img[margen_top:margen_bottom, :]

    # Escalar para mejor lectura (mínimo 400px de ancho)
    h2, w2 = img.shape[:2]
    if w2 < 400:
        scale = 400 / w2
        img = cv2.resize(img, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    return img

# =========================
# OCR con EasyOCR
# =========================
def ocr_placa(img):
    resultados = lector.readtext(img, detail=1, paragraph=False)

    print(f"EasyOCR resultados raw: {resultados}")

    if not resultados:
        return ""

    # Filtrar solo texto con confianza > 0.3
    textos = [
        res[1].strip().replace(" ", "").replace("-", "").upper()
        for res in resultados
        if res[2] > 0.3
    ]

    if not textos:
        return ""

    # Quedarse con el texto más largo (generalmente la placa)
    texto_final = max(textos, key=len)

    # Limpiar caracteres que no son letras ni números
    texto_final = ''.join(c for c in texto_final if c.isalnum())

    return texto_final

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
    print(f"Confianza detección YOLO: {confianza:.2f}")

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

    recorte_procesado = preprocesar_placa(recorte)
    texto = ocr_placa(recorte_procesado)

    print(f"Placa detectada: '{texto}'")
    return texto
