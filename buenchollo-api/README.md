# buenchollo-api

Backend FastAPI de BuenCholloTech para consultar productos de Amazon y preparar previews de chollos.

Esta API reutiliza como referencia el comportamiento que funciona en `API_Amazon_CloudCode`, pero queda desacoplada en una arquitectura modular propia. La integracion de Amazon usa el cliente `creators` con `AMAZON_API_VERSION=3.2`.

## Requisitos

- Python 3.12 o superior. Validado en este equipo con Python 3.14.
- Credenciales reales de Amazon Creators API en `.env`.
- Ejecutar los comandos desde la carpeta `buenchollo-api`.

## Instalacion

```bash
python -m pip install -r requirements.txt
```

Crea `.env` si aun no existe:

```bash
copy .env.example .env
```

Configura estas variables en `.env`:

```env
AMAZON_CLIENT_ID=...
AMAZON_CLIENT_SECRET=...
AMAZON_AFFILIATE_TAG=...
AMAZON_API_VERSION=3.2
AMAZON_CREDENTIAL_VERSION=
AMAZON_MARKETPLACE=www.amazon.es
```

No subas `.env` ni credenciales reales al repositorio.

## Arrancar la API

```bash
python -m uvicorn app.main:app --reload
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

Healthcheck:

```text
http://127.0.0.1:8000/health
```

Respuesta esperada:

```json
{
  "status": "ok",
  "app": "BuenChollo API",
  "environment": "local"
}
```

## Probar el endpoint

En Swagger, abre:

```text
POST /products/preview-from-url
```

Payload de prueba:

```json
{
  "url": "B0DTHWQJXN"
}
```

Tambien puedes probar una URL de Amazon:

```json
{
  "url": "https://www.amazon.es/dp/B0DTHWQJXN"
}
```

Respuesta esperada: `200 OK` con datos normalizados del producto:

```json
{
  "title": "...",
  "brand": "...",
  "asin": "...",
  "product_url": "...",
  "affiliate_url": "...",
  "image_url": "...",
  "current_price": 329.99,
  "original_price": 349.99,
  "discount_percentage": 6,
  "store": "Amazon",
  "category": "...",
  "description": "...",
  "telegram_text": "..."
}
```

Ejemplo con PowerShell:

```powershell
$body = @{ url = "B0DTHWQJXN" } | ConvertTo-Json
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/products/preview-from-url" `
  -Method POST `
  -Body $body `
  -ContentType "application/json"
```

## Si el puerto 8000 esta ocupado

El error tipico es:

```text
[WinError 10013] Intento de acceso a un socket no permitido por sus permisos de acceso
```

Comprueba que proceso usa el puerto:

```powershell
netstat -ano | Select-String ':8000'
```

Para parar una instancia vieja de `uvicorn`, identifica el PID y ejecuta:

```powershell
Stop-Process -Id <PID> -Force
```

Luego vuelve a arrancar:

```bash
python -m uvicorn app.main:app --reload
```

## Tests

```bash
python -m pytest
```

