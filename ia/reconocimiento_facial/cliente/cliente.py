import requests
import os

# URL del servidor Flask (la que aparece en consola al correr app.py)
URL = 'http://192.168.1.71:5000/reconocer'

# Ruta de la imagen que quieres enviar
# Esta ruta es relativa al archivo cliente.py
ruta_imagen = os.path.join('..', 'servidor_flask', 'imagenes_recibidas', 'will-smith.jpg')

# Verifica que la imagen exista
if not os.path.exists(ruta_imagen):
    print(f"ERROR: La imagen no existe en la ruta: {ruta_imagen}")
    exit()

# Abrir la imagen en modo binario y enviar al servidor
with open(ruta_imagen, 'rb') as f:
    archivos = {'imagen': f}
    try:
        respuesta = requests.post(URL, files=archivos)
        # Mostrar la respuesta del servidor
        print("Respuesta del servidor:", respuesta.json())
    except requests.exceptions.RequestException as e:
        print("Error al conectar con el servidor:", e)

