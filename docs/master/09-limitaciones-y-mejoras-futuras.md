# 09 — Limitaciones y mejoras futuras

> Documentar las limitaciones explícitamente es tan importante como
> documentar las funcionalidades. Una limitación reconocida es una
> deuda gestionable; una limitación oculta es un riesgo.

## Limitaciones actuales del proyecto

### Funcionales

| Limitación | Impacto | Defensa |
|---|---|---|
| **Sin notificaciones por email** | Los usuarios sólo reciben avisos in-app + Telegram público | Decisión consciente: priorizar el primer canal (in-app) y dejar la elección de proveedor SMTP (Resend / Sendgrid / Supabase Edge Function) para después de validar audiencia. El modelo `Alert.notify_email` ya está preparado |
| **Sin filtrado avanzado en la bandeja de notificaciones** | El usuario ve todas sus notificaciones en orden cronológico, sin posibilidad de filtrar por tipo o agrupar por alerta | El volumen actual de notificaciones por usuario es bajo. Si crece, se añade |
| **Sin marcado individual de leído** | Al cargar `/notificaciones`, se marcan **todas** como leídas | Diseño simplificado del MVP. Habilitar marcado individual es trivial cuando se justifique |
| **Matching de alertas básico** | El algoritmo soporta substring + tokens, pero no sinónimos, stemming ni búsqueda semántica con embeddings | Para el volumen actual de chollos y alertas, el matching tolerante (mayúsculas/minúsculas, acentos, frase exacta o todos los tokens) es suficiente |
| **Sin notificaciones push (PWA)** | Los usuarios sólo ven el badge al volver a la pestaña, no reciben push del navegador | La PWA con `Notification API` requiere Service Worker, permisos del usuario y un sistema de envío. Decisión: priorizar in-app + Telegram |
| **Single admin** | Sólo el autor del proyecto puede publicar | Es el modelo deliberado del producto (curación humana de calidad). Cambiar a multi-admin requeriría panel de gestión de roles, permisos granulares y auditoría más rigurosa |

### Técnicas

| Limitación | Impacto | Defensa |
|---|---|---|
| **`admin.chollos.tsx` con 940 líneas** | God Component que es difícil de mantener | Partirlo conlleva alto riesgo de regresión y los integration tests no cubren todavía toda la lógica interactiva. Documentado como deuda asumida |
| **`style-src 'unsafe-inline'` en CSP** | Permite styles inline (no scripts) | React + shadcn inyectan styles inline. Migrar a nonces es un sprint completo de coste alto |
| **JWT del usuario en `localStorage`** | Vulnerable a XSS-roba-token | Default del SDK Supabase. Cookies HttpOnly requeriría custom storage + endpoint server-side de refresh. Mitigado con CSP estricta y ESLint sin `dangerouslySetInnerHTML` |
| **A11y warnings en formularios admin** | Botones de icono sin `title`, selects sin `label` | Visibles en SonarLint del IDE. No bloquean uso, no se han priorizado para el MVP |
| **Tests integración no corren en CI** | Cobertura visible sólo en local | Requieren PostgreSQL real (Supabase no levantable en CI). Se ejecutan en local antes de cada release |
| **Tests E2E con SSR** | `page.route` no intercepta llamadas del servidor TanStack Start | Los E2E se limitan a verificar shell, rutas y guards (no contenido dinámico). Resto cubierto por integration tests |
| **Sin DAST automatizado** | Vulnerabilidades dinámicas se detectan sólo manualmente | OWASP ZAP en CI es 2+ min adicionales por run sin valor añadido relevante para el tamaño actual |
| **Sin SBOM** | No hay inventario formal de dependencias para auditorías externas | Para una entrega de TFM con un solo proyecto, el `package-lock.json` + `requirements.txt` cumplen la función |

### De infraestructura

| Limitación | Impacto | Defensa |
|---|---|---|
| **Despliegue en NAS doméstico** | Si el ISP cae, el NAS se apaga o la IP cambia sin DDNS actualizado, la web cae | Para un MVP con audiencia inicial pequeña es proporcional al riesgo. Migración a VPS / Cloudflare Tunnel está documentada en `docs/project/08-deployment.md` |
| **Sin múltiples instancias** | No hay alta disponibilidad ni balanceo | Innecesario al volumen actual. Si crece, SlowAPI tiene soporte de Redis para storage compartido |
| **Sin backup automatizado** | Si Supabase pierde un proyecto, no hay snapshot diario propio | Supabase free tier tiene backups limitados pero existentes; para datos críticos habría que añadir export periódico |
| **Sin CDN del frontend** | El frontend se sirve desde el NAS | Si se mueve a dominio definitivo, se servirá desde Cloudflare Pages o se pondrá Cloudflare delante del NAS |

### Decisiones conscientes que limitan capacidades

Estas no son "limitaciones a resolver", son **decisiones diseñadas
para optimizar otra cosa**:

- **Monolito modular** en vez de microservicios → optimizamos
  mantenibilidad y simplicidad operativa sobre escalabilidad horizontal.
- **API Gateway** en vez de BaaS directo → optimizamos seguridad y
  uniformidad sobre velocidad de iteración inicial.
- **TS strict + ESLint estricto** → ralentiza la escritura pero captura
  errores que costarían días depurar.
- **Pirámide de testing con pocos E2E** → optimizamos velocidad de
  feedback (un E2E roto tarda 6 segundos en detectarse, una regresión
  manual semanas).

## Mejoras técnicas

### Corto plazo (1–2 sprints)

- **Email para notificaciones críticas** con proveedor a elegir
  (Resend recomendado por su simplicidad). Implementación en
  `AlertMatcher.notify_matching_alerts()` que ya tiene punto de
  integración natural.
- **Refactor de `admin.chollos.tsx`** en sub-componentes:
  `<AdminDealForm>`, `<AdminDealList>`, `<DuplicateConflictDialog>`,
  `<AmazonAutocompleteSection>`, `<TelegramPanelSection>`. Estimación:
  1 sprint con tests previos.
- **Marcado individual de notificaciones**: endpoint
  `PATCH /v1/notifications/{id}/read` y UI con check individual.

### Medio plazo

- **PWA con Service Worker y push notifications**: convertir la
  app en instalable, recibir push del navegador para chollos
  matcheados.
- **Búsqueda semántica con embeddings**: usar OpenAI embeddings para
  matching de alertas avanzado (sinónimos, intención).
- **Vista de tienda** (`/tienda/{slug}`) con logo + descripción + lista
  de chollos activos por tienda.
- **Sistema de niveles/reputación** para usuarios activos (votos
  útiles, comentarios apreciados).
- **Webhook a Discord** además de Telegram para canales alternativos.

### Largo plazo

- **App móvil nativa** con React Native + Expo (puede reutilizar
  hooks de TanStack Query y servicios API existentes).
- **Multi-administrador** con panel de gestión de roles y auditoría
  más estricta.
- **Internacionalización** (`i18next`) para mercados de habla
  inglesa o italiana.
- **Mercado abierto de propuestas**: los usuarios proponen chollos
  que entran en una cola de revisión del admin antes de
  publicarse.

## Mejoras de seguridad

| Mejora | Estado actual | Justificación de no hacerlo ya |
|---|---|---|
| **2FA TOTP para administradores en código** | Configuración externa: Supabase admin tiene 2FA en su cuenta personal | Para single admin con cuenta única, es proporcional |
| **Migración JWT a cookies HttpOnly** | localStorage (default Supabase SDK) | Alto coste, SDK no lo soporta idiomáticamente, mitigado con CSP |
| **DAST automatizado con OWASP ZAP** | Manual via `securityheaders.com` y `ssllabs.com/ssltest` | Coste CI alto sin valor añadido al tamaño actual |
| **SBOM con CycloneDX** | Lockfiles + Dependabot | Para un TFM con un solo repo, lockfiles son SBOM funcional |
| **WAF / Cloudflare front** | Reverse proxy DSM con HTTPS termina aquí | Depende del dominio definitivo; documentado en pre-go-live |
| **Migración de python-multipart si surgen CVEs** | Pin 0.0.27 (0 CVEs hoy) | Automatizado vía Dependabot |
| **Rotación periódica de claves Supabase / Amazon / OpenAI** | Procedimiento documentado en `docs/project/07-security.md` | Manual hoy, automatizable con scripts |
| **Política de retención de logs Sentry** | Default 30 días en el plan gratuito | Suficiente para forensic básico |
| **Política de retención de `admin_audit_log`** | Indefinida en BD | Si crece, particionar por mes o archivar a S3 |

## Mejoras de rendimiento

| Mejora | Estado actual | Cuándo aplicar |
|---|---|---|
| **Cache de respuestas Amazon Creators API** | Sin cache | Si el admin pasa de 1 producto/min a 10+/min consistentemente |
| **Cache de respuestas OpenAI** (mismo título → mismo copy) | Sin cache | Igual que el anterior |
| **CDN para imágenes** | Servidas desde Supabase Storage directamente | Cuando se mueva al dominio definitivo y Cloudflare cubra todo el tráfico |
| **Paginación cursor-based** | Offset/limit | Si supera 10.000 chollos publicados |
| **Server-side caching con Redis** | Sin cache | Si los endpoints públicos sufren bajo carga |
| **Compresión gzip/brotli en reverse proxy** | Por defecto en DSM | Verificar al pre-go-live |
| **Image optimization automatizada** (WebP, sizes responsive) | Imagen original sin optimizar | Cuando se ponga CDN delante |
| **Lighthouse-CI automatizado** | Métricas documentadas pero no automatizadas | Si se entrega a usuarios externos con SLAs |

Performance budget documentado en `docs/QUALITY.md` (movido a master):

| Métrica | Objetivo |
|---|---|
| LCP | < 2.5 s en 3G fast |
| CLS | < 0.1 |
| INP | < 200 ms |
| Bundle inicial gzip | < 250 KB |

## Mejoras de testing

- **Tests E2E con backend real** en CI (levantar Postgres con
  GitHub Actions services, aplicar migraciones, ejecutar
  pytest -m integration). Coste: ~30 s extra por run.
- **Visual regression** con `toHaveScreenshot` sobre páginas
  estables (`/login`, `/error`). Hoy aplazado por brittleness.
- **Mutation testing** con `mutmut` o `cosmic-ray` para validar
  que los tests CORE son robustos.
- **Property-based testing** con `hypothesis` para validar funciones
  de cálculo (`calculateDiscount`, `slugify`).
- **Page Object Model elaborado** cuando los E2E pasen de 20.

## Mejoras de documentación

- **Diagramas de secuencia** para flujos críticos (creación de
  chollo con autocomplete, match de alerta con notificación) en
  `docs/master/03-analisis-funcional.md`.
- **Diagramas C4** (Context, Container, Component, Code) en
  `docs/master/04-arquitectura-y-decisiones-tecnicas.md`.
- **Vídeos cortos de demo** del proyecto (Loom) enlazados desde el
  `README.md`.
- **OpenAPI documentación pública** si el backend pasa a ser API
  pública.
- **Changelog formal** además del `PROJECT_STATUS.md` (los releases
  podrían usar `git-cliff` o similar para generarlo automáticamente).

## Posible evolución del producto

Si BuenCholloTech sale del ámbito académico y se convierte en
producto real, los pasos naturales:

1. **Comprar dominio** y configurar Cloudflare (CDN + DNS + DDoS
   básico).
2. **Migrar a Supabase plan Pro** o equivalente para audit logs más
   amplios, point-in-time recovery y soporte.
3. **Añadir analytics** (Plausible o Umami autohospedado para no
   tracking invasivo).
4. **Sistema de afiliados ampliado** (PCComponentes, MediaMarkt,
   Aliexpress). Cada uno como adapter del Protocol
   `ProductPreviewProvider`.
5. **Newsletter semanal** con resumen automatizado de los chollos
   más calientes.
6. **Sistema de premios al usuario** (badges, ranking comunitario).
7. **App móvil** y push notifications.
8. **Multi-administrador** con panel de moderación.
9. **Monetización** (banner discreto, programa de afiliados
   ampliado, suscripción Premium con alertas instantáneas y
   prioridad).

Estas son ideas, no compromisos. El proyecto cierra para TFM con el
MVP funcional descrito en este documento; cualquier evolución
posterior será decisión deliberada con su propio análisis de
viabilidad.
