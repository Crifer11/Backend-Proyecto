import cv2
import torch
import pytesseract
import numpy as np
import os
from huggingface_hub import hf_hub_download

# =========================
# Cargar modelo YOLO UNA SOLA VEZ
# Descargando desde Hugging Face directamente
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
    alto, ancho = img.shape[:2]
    if ancho < 200:
        scale = 200 / ancho
        img = cv2.resize(img, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gris = cv2.bilateralFilter(gris, 11, 17, 17)
    binaria = cv2.adaptiveThreshold(
        gris,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        15
    )
    kernel = np.ones((3, 3), np.uint8)
    procesada = cv2.morphologyEx(binaria, cv2.MORPH_CLOSE, kernel)
    return procesada

# =========================
# OCR
# =========================
def ocr_placa(img):
    config = "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    texto = pytesseract.image_to_string(img, config=config)
    texto = texto.strip().replace(" ", "").replace("-", "").replace("\n", "")
    return texto if texto else ""

# =========================
# FUNCIÓN PRINCIPAL
# =========================
def reconocer_placa(imagen_bgr):
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
