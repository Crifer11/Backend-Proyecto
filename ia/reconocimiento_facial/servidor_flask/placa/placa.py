import cv2
import torch
import pytesseract
import numpy as np
import os

# =========================
# Cargar modelo YOLO UNA SOLA VEZ
# Usando el modelo keremberke/yolov5m-license-plate
# que es el modelo base correctamente entrenado
# =========================
print("Cargando modelo YOLOv5 de placas...")
modelo = torch.hub.load(
    "keremberke/yolov5",
    "custom",
    model_name="yolov5m",
    pretrained=True,
    channel="license-plate",
    force_reload=False,
    trust_repo=True
)
modelo.conf = 0.3  # umbral de confianza un poco más bajo para detectar más casos
modelo.iou  = 0.45
print("Modelo de placas cargado correctamente")

# =========================
# Preprocesamiento
# =========================
def preprocesar_placa(img):
    # Escalar la imagen para que Tesseract trabaje mejor
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
    # psm 7: trata la imagen como una sola línea de texto
    # psm 8: trata la imagen como una sola palabra (alternativa)
    config = "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    texto = pytesseract.image_to_string(img, config=config)
    texto = texto.strip().replace(" ", "").replace("-", "").replace("\n", "")
    return texto if texto else ""

# =========================
# FUNCIÓN PRINCIPAL
# =========================
def reconocer_placa(imagen_bgr):
    """
    imagen_bgr: numpy array en formato BGR (como lo entrega OpenCV)
    return: texto de la placa detectada o "" si no se detectó
    """
    if imagen_bgr is None:
        return ""

    resultados = modelo(imagen_bgr, size=640)
    detecciones = resultados.xyxy[0]

    print(f"Detecciones YOLO: {len(detecciones)}")

    if len(detecciones) == 0:
        return ""

    # Tomar la mejor detección por confianza
    mejor = detecciones[detecciones[:, 4].argmax()]
    confianza = float(mejor[4])
    print(f"Confianza detección: {confianza:.2f}")

    x1, y1, x2, y2 = map(int, mejor[:4])

    # Agregar un pequeño margen al recorte
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
