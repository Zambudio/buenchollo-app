# 🚀 Arquitectura de Despliegue — BuenChollo API (NAS Synology)

Este documento detalla la infraestructura utilizada para desplegar el backend de **BuenCholloTech** en un entorno de producción doméstico sobre un NAS Synology.

---

## 1. Vista general del sistema

`buenchollo-api` es el **API Gateway** de la plataforma: centraliza la lógica de negocio, la autenticación JWT y el acceso a la base de datos. Está construido con **FastAPI** (Python 3.12+) y desplegado como contenedor Docker en el NAS.

### Flujo de datos completo

```
Usuario (Browser)
        │  HTTPS :8000
        ▼
Router doméstico
        │  Port Forward → NAS IP 192.168.1.3
        ▼
NAS Synology DSM — Proxy Inverso
        │  HTTP interno → Contenedor Docker
        ▼
Docker (buenchollo-api)  ← puerto interno 8000
        │
        ├──► PostgreSQL (Supabase, aws-0-eu-central-1.pooler.supabase.com:6543)
        ├──► Supabase Auth API (validación JWT)
        ├──► Amazon Creators API (scraping)
        └──► OpenAI API (enriquecimiento con IA)
```

---

## 2. Infraestructura Docker

### Dockerfile
- Imagen base: `python:3.12-slim` (ligera, sin herramientas de compilación innecesarias).
- Instala dependencias desde `requirements.txt`, incluyendo `asyncpg`, `sqlalchemy[asyncio]` y `python-amazon-paapi`.

### Docker Compose
- **Mapeo de puertos**: El contenedor expone el puerto `8000` internamente. El proxy inverso del NAS lo hace accesible externamente también por el puerto `8000` (HTTPS).
- **Variables de entorno**: Se cargan desde el archivo `.env` en el volumen del NAS (no incluido en el repositorio).
- **Restart policy**: `unless-stopped` — el contenedor se reinicia automáticamente si el NAS se reinicia.

---

## 3. Acceso externo y seguridad

### A. DDNS (Dynamic DNS)
Se utiliza el servicio DDNS de Synology para vincular la IP dinámica del hogar al dominio fijo:
- **Dominio**: `embyZambu.synology.me`
- **Protocolo externo**: HTTPS (puerto 8000), con certificado SSL gestionado automáticamente por DSM (Let's Encrypt).

### B. Proxy Inverso (Synology DSM)
Configurado en *Panel de Control → Portal de inicio de sesión → Proxy inverso*:

| Campo | Valor |
|---|---|
| Protocolo entrada | HTTPS |
| Puerto entrada | 8000 |
| Destino | HTTP → localhost |
| Puerto destino | 8000 (contenedor Docker) |

El proxy inverso centraliza la terminación TLS: el contenedor solo maneja HTTP, sin necesidad de gestionar certificados.

### C. Router (Port Forwarding)
- **Puerto**: 8000 TCP → IP del NAS (`192.168.1.3`).

---

## 4. CORS

El middleware de CORS en `main.py` solo permite orígenes configurados en la variable `CORS_ORIGINS` del `.env`:

```env
# Producción
CORS_ORIGINS=https://buenchollotech.com,https://www.buenchollotech.com

# Desarrollo local
CORS_ORIGINS=*
```

Los orígenes se validan petición a petición. El preflight (`OPTIONS`) se responde directamente desde el middleware con `204 No Content` para máxima compatibilidad con browsers.

---

## 5. Scheduler de limpieza

`DealCleanerService` se ejecuta automáticamente cada día a las 03:00 AM mediante **APScheduler**, gestionado por el `lifespan` de FastAPI:

- Si el scheduler no está disponible (p.ej. la dependencia no está instalada), la API arranca igualmente sin él.
- Logs de inicio/parada: busca `"scheduler"` en los logs del contenedor.

---

## 6. Procedimiento de actualización

Cuando se realizan cambios en el código:

1. **Copiar archivos modificados al NAS** (vía File Station o `scp`):
   ```
   /volume1/docker/buenchollo-api/
   ```
2. **Reconstruir y relanzar el contenedor** (por SSH en el NAS):
   ```bash
   cd /volume1/docker/buenchollo-api
   sudo docker-compose up -d --build
   ```
3. **Verificar**:
   ```
   https://embyZambu.synology.me:8000/health
   ```

---

## 7. Diagnóstico en producción

| Situación | Acción |
|---|---|
| API no responde | Comprobar el contenedor en Container Manager y los logs |
| Error 401 al guardar chollos | Llamar a `/auth/me` con la sesión iniciada; verificar `is_admin` |
| Error de BD | Revisar `DATABASE_URL` en el `.env` del NAS (debe ser connection pooler, puerto 6543) |
| CORS bloqueado | Verificar que el dominio del frontend está en `CORS_ORIGINS` del `.env` |

---

*Documentación del Proyecto de Fin de Máster en Desarrollo con IA (2025)*  
*Actualizado: 19 de Mayo de 2026*
