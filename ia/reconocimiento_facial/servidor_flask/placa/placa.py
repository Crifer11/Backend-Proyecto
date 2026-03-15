# placas.py - deteccion y OCR de placas EN MEMORIA
import cv2
import torch
import pytesseract
import numpy as np
import os

# =========================
# Cargar modelo YOLO UNA SOLA VEZ
# =========================
BASE_DIR = os.path.dirname(__file__)
MODEL_FILE = os.path.join(BASE_DIR, "best.pt")

print("Cargando modelo YOLOv5 de placas...")

modelo = torch.hub.load(
    "ultralytics/yolov5",
    "custom",
    path=MODEL_FILE,
    force_reload=False
)

modelo.conf = 0.4

print("Modelo de placas cargado correctamente")

# =========================
# Preprocesamiento
# =========================
def preprocesar_placa(img):
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

    config = "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNÑOPQRSTUVWXYZ0123456789"

    texto = pytesseract.image_to_string(img, config=config)

    texto = texto.strip().replace(" ", "").replace("-", "")

    return texto if texto else ""

# =========================
# FUNCIÓN PRINCIPAL
# =========================
def reconocer_placa(imagen_bgr):

    if imagen_bgr is None:
        return ""

    resultados = modelo(imagen_bgr, size=640)

    detecciones = resultados.xyxy[0]

    if len(detecciones) == 0:
        return ""

    # mejor detección por confianza
    mejor = detecciones[detecciones[:,4].argmax()]

    x1, y1, x2, y2 = map(int, mejor[:4])

    recorte = imagen_bgr[y1:y2, x1:x2]

    if recorte.size == 0:
        return ""

    procesada = preprocesar_placa(recorte)

    texto = ocr_placa(procesada)

    return texto
