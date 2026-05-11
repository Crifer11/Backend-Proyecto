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
    trust_repo=True,
    skip_validation=True
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
# Distancia de Levenshtein
# =========================
def levenshtein(s1, s2):
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    fila_anterior = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        fila_actual = [i + 1]
        for j, c2 in enumerate(s2):
            inserciones   = fila_anterior[j + 1] + 1
            eliminaciones = fila_actual[j] + 1
            sustituciones = fila_anterior[j] + (c1 != c2)
            fila_actual.append(min(inserciones, eliminaciones, sustituciones))
        fila_anterior = fila_actual
    return fila_anterior[-1]

def comparar_placa(placa_detectada, placa_registrada, tolerancia=1):
    """
    Compara la placa detectada contra la registrada.
    Retorna True si son iguales o si la diferencia es <= tolerancia.
    """
    p1 = placa_detectada.upper().replace("-", "").replace(" ", "")
    p2 = placa_registrada.upper().replace("-", "").replace(" ", "")
    distancia = levenshtein(p1, p2)
    print(f"Comparando '{p1}' vs '{p2}' — distancia: {distancia}")
    return distancia <= tolerancia

# =========================
# Preprocesamiento
# =========================
def preprocesar_placa(img):
    h, w = img.shape[:2]

    # Recortar solo la franja del texto principal
    margen_top    = int(h * 0.28)
    margen_bottom = int(h * 0.72)
    img = img[margen_top:margen_bottom, :]

    # Escalar para mejor lectura
    h2, w2 = img.shape[:2]
    if w2 < 400:
        scale = 400 / w2
        img = cv2.resize(img, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    return img

# =========================
# OCR con EasyOCR (sin allowlist — mejor detección)
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

    # Quedarse con el texto más largo
    texto_final = max(textos, key=len)
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
