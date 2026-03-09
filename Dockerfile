FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    cmake \
    g++ \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Instalar dlib-bin PRIMERO para que face-recognition no intente compilar dlib
RUN pip install --no-cache-dir dlib-bin

COPY requirements.txt .
# Instalar el resto ignorando dlib ya que está instalado
RUN pip install --no-cache-dir -r requirements.txt --no-deps face-recognition==1.3.0 \
    && pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
