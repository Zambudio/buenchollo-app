FROM python:3.11-slim

# Evitar que Python genere archivos .pyc y habilitar logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Usuario no-root (AUDIT_REPORT M-01 / TD-13): un compromiso de la app no
# obtiene root dentro del contenedor. Sin home ni shell: solo ejecuta uvicorn.
# La app no escribe en disco (logs a stdout, PYTHONDONTWRITEBYTECODE=1), así
# que basta con permiso de lectura sobre /app.
RUN useradd --no-create-home --shell /usr/sbin/nologin app
USER app

# Exponer el puerto que usará uvicorn
EXPOSE 8000

# Liveness para Container Manager / docker ps: usa el /health de la propia
# API (sin dependencias extra — python ya está en la imagen).
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)"]

# Comando para ejecutar la aplicación
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
