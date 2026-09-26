# ADR-014: Analítica first-party con atribución por sesión

- **Estado**: ✅ Aceptado
- **Fecha**: 2026-09-26
- **Autor**: BuenChollo Tech Team

---

## Contexto

Se necesita conocer cuántas personas visitan la web y los artículos, distinguir visitas de
visitantes, y atribuir el recorrido completo a Telegram, buscadores, referencias externas o acceso
directo. Los enlaces de Telegram apuntan a la portada, por lo que el origen debe conservarse si la
persona navega después hacia el blog. También se requiere un contador público por artículo y evitar
que las comprobaciones del administrador distorsionen los datos.

## Decisión

1. Implementar el módulo `app/modules/analytics` dentro del monolito FastAPI y persistir los eventos
   en PostgreSQL mediante el API Gateway.
2. Generar en el navegador un identificador aleatorio de visitante y otro de sesión. La API almacena
   únicamente su HMAC-SHA256, nunca los identificadores originales ni la IP.
3. Aplicar atribución *first-touch* durante una sesión de 30 minutos de inactividad. La prioridad es
   UTM explícita, buscador reconocido, referencia externa y, por último, acceso directo.
4. Publicar `/telegram` como entrada canónica que redirige a
   `/?utm_source=telegram&utm_medium=social&utm_campaign=canal`. El generador de publicaciones
   debe usar `https://buenchollotech.com/telegram` para el enlace general hacia la web, sin cambiar
   el enlace de compra del producto.
5. Contabilizar el contador público del blog una vez por navegador, artículo y día mediante una
   tabla de unicidad; conservar todos los pageviews para el análisis interno.
6. Excluir automáticamente rutas administrativas y administradores, y ofrecer una preferencia local
   para excluir cualquier dispositivo.
7. Limitar los eventos a 25 meses y ejecutar una limpieza diaria desde el scheduler existente.
8. Mostrar el agregado únicamente a administradores, con periodos de 7, 30 y 90 días y foco en la
   conversión Telegram → blog.

## Alternativas consideradas

- **Google Analytics**: descartado para evitar terceros, cookies publicitarias y complejidad de
  consentimiento no necesaria para el objetivo.
- **Cloudflare Web Analytics como única fuente**: útil para tráfico global, pero insuficiente para el
  contador por artículo y la atribución first-touch del recorrido Telegram → portada → blog.
- **Contador simple en `blog_posts`**: descartado como fuente única porque no distingue personas,
  sesiones, origen ni repeticiones.

## Consecuencias

- La aplicación controla el dato y puede responder las preguntas del canal sin depender de un SaaS.
- La métrica de visitante representa un navegador, no una persona física; borrar almacenamiento o
  cambiar de dispositivo genera una identidad nueva.
- Navegadores que bloquean almacenamiento no se miden y la navegación continúa normalmente.
- La base de datos debe aplicar la migración `20260926120000` antes de desplegar el código.
- `ANALYTICS_HASH_SECRET` debe configurarse con un secreto largo e independiente en producción.
