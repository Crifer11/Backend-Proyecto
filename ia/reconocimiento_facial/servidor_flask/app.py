
# ESTE CODIGO ES DE app.py UNIFICADO

from flask import Flask, request, jsonify
import os
from facial.facial import reconocer_rostro   # Reconocimiento facial

app = Flask(__name__)

# ================================
# Carpetas donde se guardan imagenes
# ================================

UPLOAD_FOLDER_FACIAL = os.path.join(os.path.dirname(__file__), 'imagenes_faciales_recibidas')
UPLOAD_FOLDER_PLACA = os.path.join(os.path.dirname(__file__), 'imagenes_placas_recibidas')


os.makedirs(UPLOAD_FOLDER_FACIAL, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_PLACA, exist_ok=True)

# ================================
# ENDPOINT PARA RECONOCIMIENTO FACIAL
# ================================
@app.route('/upload_facial', methods=['POST'])
def upload_facial():
    if not request.data:
        return jsonify({"status": "ERROR", "message": "No se recibio imagen"}), 400

    filename = "ultima_facial.jpg"
    filepath = os.path.join(UPLOAD_FOLDER_FACIAL, filename)

    try:
        with open(filepath, "wb") as f:
            f.write(request.data)

        print(f" Imagen facial recibida y guardada como {filename}")

        resultado = reconocer_rostro(filepath)
        print(f"  Resultado reconocimiento facial: {resultado}")

        if "Match encontrado con" in resultado:
            persona = resultado.split("Match encontrado con:")[-1].strip()
            return jsonify({"status": "MATCH", "persona": persona})

        elif "No se encontro match" in resultado:
            return jsonify({"status": "NO_MATCH"})

        elif "No se detecto ningun rostro" in resultado:
            return jsonify({"status": "NO_FACE"})

        else:
            return jsonify({"status": "ERROR", "message": resultado})

    except Exception as e:
        print(f" Error en reconocimiento facial: {e}")
        return jsonify({"status": "ERROR", "message": str(e)})

# ================================
# ENDPOINT PARA RECONOCIMIENTO DE PLACAS
# ================================
@app.route('/upload_placa', methods=['POST'])
def upload_placa():
    if not request.data:
        return jsonify({"status": "ERROR", "message": "No se recibio imagen"}), 400

    filename = "ultima_placa.jpg"
    filepath = os.path.join(UPLOAD_FOLDER_PLACA, filename)

    try:
        with open(filepath, "wb") as f:
            f.write(request.data)

        print(f" Imagen de placa recibida y guardada como {filename}")

        #  Aqui luego conectaremos la IA de placas (OCR/YOLO)
        
        return jsonify({"status": "OK", "message": "Imagen de placa recibida correctamente"})

    except Exception as e:
        print(f" Error en reconocimiento de placa: {e}")
        return jsonify({"status": "ERROR", "message": str(e)})

# ================================
# MAIN
# ================================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
