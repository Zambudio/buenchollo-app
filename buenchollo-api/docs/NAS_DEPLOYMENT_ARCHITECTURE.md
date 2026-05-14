# 🚀 Documentación de Arquitectura y Despliegue: BuenChollo API

Este documento detalla la infraestructura y configuración utilizada para desplegar el backend de **BuenCholloTech** en un entorno de producción doméstico pero profesional utilizando un servidor NAS Synology.

## 1. Vista General del Sistema
La API de BuenChollo es un servicio basado en **FastAPI** (Python 3.12+) encargado de la comunicación con la Amazon Creators API, el procesamiento de datos y la generación de contenido enriquecido para chollos.

## 2. Infraestructura de Despliegue: Docker
Para garantizar la portabilidad y el aislamiento, el servicio se ha "dockerizado".

### Archivos de Configuración:
- **Dockerfile**: Utiliza una imagen base ligera (`python:3.11-slim`). Instala las dependencias necesarias, incluyendo la integración con Amazon mediante `python-amazon-paapi`.
- **Docker Compose**: Orquestra el despliegue definiendo:
  - **Mapeo de puertos**: Puerto externo **8001** (NAS) -> Puerto interno **8000** (Contenedor).
  - **Gestión de secretos**: Uso de archivo `.env` (no incluido en el repo).

## 3. Estrategia de Acceso Externo y Seguridad

### A. DDNS (Dynamic DNS)
Se utiliza el dominio `embyZambu.synology.me` para vincular la IP doméstica a un host fijo.

### B. Proxy Inverso (Synology DSM)
- **Protocolo Externo**: HTTPS (Puerto 8000).
- **Redirección Interna**: HTTP (Puerto 8001).
- **Razón**: Permite centralizar certificados SSL en el NAS y evitar conflictos de puertos.

### C. Configuración del Router
- **Port Forwarding**: Puerto 8000 redirigido a la IP del NAS (`192.168.1.3`).

## 4. Desarrollo de Software y Middleware

### Gestión de CORS (Cross-Origin Resource Sharing)
Se ha habilitado `CORSMiddleware` en FastAPI para permitir peticiones desde el frontend web externo.

### Integración con Amazon Creators API (v3.2)
Sustitución de librerías locales por `python-amazon-paapi` para asegurar compatibilidad con el sistema LWA de Amazon.

## 5. Flujo de Datos
`Usuario (Web) -> HTTPS:8000 -> Router -> NAS (Proxy Inverso) -> Docker:8001 -> FastAPI`

---
*Documentación generada para el Proyecto de Fin de Máster en Desarrollo con IA (2025)*
