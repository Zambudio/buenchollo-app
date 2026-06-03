# 01 — Introducción del proyecto

## Presentación

**BuenCholloTech** es una plataforma web de comunidad para descubrir,
publicar, gestionar y automatizar ofertas tecnológicas (chollos
tech): monitores, periféricos, móviles, audio, gaming, componentes,
etc. Combina la curación humana de un administrador con un sistema de
alertas personalizadas, votación comunitaria y publicación
automatizada al canal de Telegram del proyecto.

El proyecto se presenta como **Trabajo Final del Máster en Desarrollo
con IA 2025**, pero se ha diseñado y construido con vocación de
producto personal a medio plazo. Las decisiones técnicas no se
limitan al alcance académico: están orientadas a un sistema que
seguirá creciendo y manteniéndose más allá de la entrega.

## Contexto

En el ecosistema español hay numerosos foros y canales de Telegram
dedicados a "chollos" tecnológicos. El más conocido (Chollometro) es
una comunidad abierta donde el contenido depende del voto colectivo y
los usuarios proponen ofertas en bruto. Existen también canales más
verticales (PCComponentes, Amazon, MediaMarkt, etc.) y agregadores que
copian sin filtro y dependen del SEO.

**BuenCholloTech** se sitúa en un punto intermedio: una comunidad
abierta con vista pública para usuarios anónimos, pero con curación
humana del administrador para garantizar calidad. Las ofertas las
publica un único responsable (el autor del proyecto) y la plataforma se
encarga de:

- Enriquecer cada chollo con metadatos automáticos: imagen, precio
  histórico, descripción técnica, copy adaptado para Telegram, todo
  ello generado a partir de la URL del producto en Amazon mediante la
  Creators API y OpenAI.
- Distribuir notificaciones a los usuarios suscritos a alertas
  personalizadas (por palabra clave, categoría, tienda, marca o
  descuento mínimo).
- Publicar simultáneamente en la web y en el canal público de
  Telegram con un copy adaptado a cada medio.

## Motivación

### Motivación personal

El autor mantiene un canal informal de Telegram donde comparte
ofertas tecnológicas con un grupo reducido de personas. Lo que empezó
como mensajes ocasionales se convirtió en una rutina de buscar
manualmente productos, escribir el texto, sacar la imagen, calcular el
descuento y enviar. **El objetivo personal es automatizar todo ese
flujo manual** para poder escalar a una audiencia mayor y, en su caso,
abrirlo como producto real con su propio dominio.

### Motivación académica

El máster cubre arquitectura de software, calidad, seguridad y uso de
IA. **BuenCholloTech permite poner en práctica los cuatro bloques
sobre un único producto real**, no sobre un ejercicio académico
sintético. Cada decisión técnica se ha tomado pensando en defenderla
ante tribunal:

- Cada gran decisión vive en un ADR firmado.
- Cada sprint tiene una bitácora cronológica en `PROJECT_STATUS.md`.
- Cada módulo del máster tiene un sprint dedicado (F1–F7
  arquitectura, Q1–Q7 calidad, S1–S7 seguridad).

## Problema que resuelve

| Problema | Cómo lo aborda BuenCholloTech |
|---|---|
| Las ofertas tech buenas se pierden entre el ruido. | Curación humana del admin: sólo entra lo que el autor considera buen chollo. |
| Buscar chollos manualmente es tedioso. | Alertas personalizadas por keyword/categoría/precio que disparan notificaciones in-app cuando aparece algo coincidente. |
| Reescribir cada publicación para distintos canales (web, Telegram) consume tiempo. | El admin pega la URL de Amazon → el sistema genera título, imagen, precio, copy Telegram y ASIN automáticamente. Publica simultáneamente. |
| Sin gráfica de precios no se sabe si una oferta es realmente buena. | Cada chollo enlaza a su gráfica Keepa por ASIN para validar el descuento contra el histórico. |
| Los agregadores genéricos son spam y no aportan contexto. | Curación + descripción técnica enriquecida + temperatura por votos. |

## Alcance del proyecto

El TFM cubre un **MVP funcional en producción** desplegado en NAS
Synology, con:

- Frontend público con feed, búsqueda y detalle de chollos.
- Sistema de autenticación con Google OAuth.
- Funciones de usuario registrado: votar, comentar, marcar favoritos,
  crear alertas, recibir notificaciones.
- Panel administrativo con CRUD completo, autocomplete desde URL de
  Amazon y publicación a Telegram.
- Pipeline de CI/CD con tests automáticos, gates de calidad y auditoría
  de seguridad.
- Documentación completa para defensa académica.

**Lo que queda fuera del alcance del TFM** (documentado como mejora
futura en [`09-limitaciones-y-mejoras-futuras.md`](09-limitaciones-y-mejoras-futuras.md)):

- Notificaciones por email.
- Múltiples administradores y panel de gestión de roles vía UI.
- Búsqueda semántica con embeddings.
- App móvil nativa.
- Internacionalización (la web es sólo en español).
- DAST automatizado y SBOM.

## Estructura del documento

El resto de la documentación del máster se organiza en 9 capítulos
(02–10). Cada uno aborda un eje de los módulos cursados, con
referencias cruzadas al código y a la documentación operativa cuando
proceda.

- Si quieres la versión **práctica** (cómo instalar, cómo ejecutar
  tests), consulta [`docs/project/`](../project/00-index.md).
- Si quieres ver **decisiones documentadas con su contexto**, consulta
  [`docs/adr/`](../adr/00-index.md).
- Si quieres **referencias técnicas densas** (auditoría OWASP completa,
  plan de hardening), consulta [`docs/reference/`](../reference/).
