# placas.py - deteccion y OCR de placas EN MEMORIA

import cv2
import torch
import pytesseract
import numpy as np
import os

# =========================
# Configurar Tesseract (Windows)
# =========================
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

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
modelo.conf = 0.4  # confianza mínima
print("Modelo de placas cargado correctamente")

# =========================
# Preprocesamiento
# =========================
def preprocesar_placa(img):
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gris = cv2.bilateralFilter(gris, 11, 17, 17)

    binaria = cv2.adaptiveThreshold(
        gris, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 15
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
# FUNCIÓN PRINCIPAL (EN MEMORIA)
# =========================
def reconocer_placa(imagen_bgr):
    """
    imagen_bgr: imagen OpenCV (numpy array)
    return: texto de placa o ""
    """

    if imagen_bgr is None:
        return ""

    # detección YOLO
    resultados = modelo(imagen_bgr)
    df = resultados.pandas().xyxy[0]

    if df.empty:
        return ""

    # mejor detección
    fila = df.sort_values(by="confidence", ascending=False).iloc[0]
    x1, y1, x2, y2 = map(int, [fila.xmin, fila.ymin, fila.xmax, fila.ymax])

    recorte = imagen_bgr[y1:y2, x1:x2]
    if recorte.size == 0:
        return ""

    # OCR
    procesada = preprocesar_placa(recorte)
    texto = ocr_placa(procesada)
    
    return texto
