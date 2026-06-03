# Despliegue de buenchollo-api en Synology NAS

Para dejar tu API siempre disponible en tu Synology NAS, usaremos **Docker** (llamado **Container Manager** en versiones modernas de DSM). Es la forma más limpia y robusta de hacerlo.

## 1. Preparación de Archivos
He creado dos archivos clave en tu proyecto:
- `Dockerfile`: Instrucciones para construir la imagen de tu API.
- `docker-compose.yml`: Configuración para lanzar el contenedor de forma sencilla.

## 2. Subir el proyecto al NAS
1. Abre **File Station** en tu Synology.
2. Ve a la carpeta `docker` (creada automáticamente al instalar Docker/Container Manager).
3. Crea una subcarpeta llamada `buenchollo-api`.
4. Sube **todo el contenido** de tu carpeta local `buenchollo-api` a esa carpeta del NAS.
   - **IMPORTANTE**: Asegúrate de subir también el archivo `.env` con tus credenciales de Amazon.

## 3. Despliegue con Container Manager (Recomendado)
Si tienes DSM 7.2+, usa **Container Manager**:
1. Abre **Container Manager**.
2. Ve a **Proyecto** (Project) y haz clic en **Crear**.
3. Ponle un nombre (ej. `buenchollo-api`).
4. En **Ruta** (Path), selecciona la carpeta que acabas de subir en el NAS.
5. Selecciona **Usar docker-compose.yml existente**.
6. Sigue el asistente (Siguiente, Siguiente) y dale a **Finalizar**.
7. El NAS empezará a construir la imagen y levantará el servicio automáticamente.

## 4. Despliegue por SSH (Alternativa rápida)
Si prefieres la terminal:
1. Activa SSH en el Panel de Control de tu Synology.
2. Conéctate desde tu PC: `ssh usuario@IP_DEL_NAS`.
3. Navega a la carpeta: `cd /volume1/docker/buenchollo-api`.
4. Ejecuta: `sudo docker-compose up -d --build`.

## 5. Acceso y Comprobación
Una vez levantado:
- Tu API estará disponible en: `http://IP_DEL_NAS:8000`
- Puedes probar el estado en: `http://IP_DEL_NAS:8000/health`
- Si quieres acceder desde fuera de tu casa:
  - Deberás abrir el puerto **8000** en tu router apuntando a la IP del NAS.
  - O mejor aún, usa el **Reverse Proxy** de Synology (Panel de Control -> Portal de inicio de sesión -> Avanzado -> Proxy inverso) para ponerle un dominio con HTTPS.

¡Listo! Tu API ahora correrá 24/7 en tu NAS.
