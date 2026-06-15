# 🔭 09 · Limitaciones y mejoras futuras

> **TL;DR** · Documentar las limitaciones explícitamente es tan
> importante como documentar las funcionalidades. Una limitación
> reconocida es deuda gestionable; una limitación oculta es un riesgo.
> Aquí están **todas las decisiones de NO hacer**, con justificación.

---

## ⚠️ Limitaciones actuales del proyecto

### 🎯 Funcionales

<table>
<thead>
<tr><th>Limitación</th><th>Impacto</th><th>Justificación</th></tr>
</thead>
<tbody>
<tr>
  <td>📧 <strong>Sin notificaciones por email</strong></td>
  <td>Los usuarios sólo reciben avisos in-app + Telegram público</td>
  <td>Decisión consciente: priorizar el primer canal (in-app) y dejar la elección de proveedor SMTP para después de validar audiencia. Modelo <code>Alert.notify_email</code> ya preparado</td>
</tr>
<tr>
  <td>🔍 <strong>Sin filtrado avanzado en la bandeja</strong></td>
  <td>El usuario ve todas sus notificaciones en orden cronológico</td>
  <td>Volumen actual de notificaciones por usuario es bajo</td>
</tr>
<tr>
  <td>✅ <strong>Sin marcado individual de leído</strong></td>
  <td>Al cargar <code>/notificaciones</code>, se marcan <strong>todas</strong> como leídas</td>
  <td>Diseño simplificado del MVP. Habilitar marcado individual es trivial cuando se justifique</td>
</tr>
<tr>
  <td>🧠 <strong>Matching de alertas básico</strong></td>
  <td>Soporta substring + tokens, pero no sinónimos, stemming ni búsqueda semántica</td>
  <td>Para el volumen actual, el matching tolerante (mayúsculas/minúsculas, acentos, frase exacta o todos los tokens) es suficiente</td>
</tr>
<tr>
  <td>🔔 <strong>Sin notificaciones push (PWA)</strong></td>
  <td>Los usuarios sólo ven el badge al volver a la pestaña</td>
  <td>PWA con <code>Notification API</code> requiere Service Worker + permisos + sistema de envío. Priorizado in-app + Telegram</td>
</tr>
<tr>
  <td>👤 <strong>Single admin</strong></td>
  <td>Sólo el autor puede publicar</td>
  <td>Es el modelo deliberado del producto (curación humana de calidad). Multi-admin requeriría panel de gestión de roles, permisos granulares y auditoría más rigurosa</td>
</tr>
</tbody>
</table>

### ⚙️ Técnicas

<table>
<thead>
<tr><th>Limitación</th><th>Impacto</th><th>Justificación</th></tr>
</thead>
<tbody>
<tr>
  <td>🪨 <strong><code>admin.chollos.tsx</code> con 940 líneas</strong></td>
  <td>God Component difícil de mantener</td>
  <td>Partirlo conlleva alto riesgo y los integration tests no cubren toda la lógica interactiva. Documentado como deuda asumida</td>
</tr>
<tr>
  <td>🎨 <strong><code>style-src 'unsafe-inline'</code> en CSP</strong></td>
  <td>Permite styles inline (no scripts)</td>
  <td>React + shadcn inyectan styles inline. Migrar a nonces es un sprint completo de coste alto</td>
</tr>
<tr>
  <td>🍪 <strong>JWT del usuario en <code>localStorage</code></strong></td>
  <td>Vulnerable a XSS-roba-token</td>
  <td>Default del SDK Supabase. Cookies HttpOnly requeriría custom storage + endpoint server-side de refresh. Mitigado con CSP estricta</td>
</tr>
<tr>
  <td>♿ <strong>A11y warnings en formularios admin</strong></td>
  <td>Botones de icono sin <code>title</code>, selects sin <code>label</code></td>
  <td>Visibles en SonarLint del IDE. No bloquean uso, no se han priorizado para el MVP</td>
</tr>
<tr>
  <td>🧪 <strong>Tests integración no corren en CI</strong></td>
  <td>Cobertura visible sólo en local</td>
  <td>Requieren PostgreSQL real (Supabase no levantable en CI). Se ejecutan en local antes de cada release</td>
</tr>
<tr>
  <td>🎭 <strong>Tests E2E con SSR</strong></td>
  <td><code>page.route</code> no intercepta llamadas server-side</td>
  <td>Los E2E se limitan a verificar shell, rutas y guards. Resto cubierto por integration tests</td>
</tr>
<tr>
  <td>🤖 <strong>Sin DAST automatizado</strong></td>
  <td>Vulnerabilidades dinámicas se detectan sólo manualmente</td>
  <td>OWASP ZAP en CI son 2+ min adicionales por run sin valor relevante para el tamaño actual</td>
</tr>
<tr>
  <td>📜 <strong>Sin SBOM</strong></td>
  <td>No hay inventario formal para auditorías externas</td>
  <td>Para un TFM con un solo proyecto, <code>package-lock.json</code> + <code>requirements.txt</code> cumplen la función</td>
</tr>
</tbody>
</table>

### 🏗️ De infraestructura

| Limitación | Impacto | Justificación |
|---|---|---|
| 🏠 **Despliegue en NAS doméstico** | Si el ISP cae, el NAS se apaga o la IP cambia sin DDNS actualizado, la web cae | Para un MVP con audiencia inicial pequeña es proporcional al riesgo. Migración a VPS / Cloudflare Tunnel documentada |
| 🔁 **Sin múltiples instancias** | No hay alta disponibilidad ni balanceo | Innecesario al volumen actual. SlowAPI tiene soporte de Redis para storage compartido |
| 💾 **Sin backup automatizado** | Si Supabase pierde un proyecto, no hay snapshot diario propio | Supabase free tier tiene backups limitados pero existentes |
| 🌐 **Sin CDN del frontend** | Se sirve desde el NAS | Si se mueve a dominio definitivo, se sirve ya desde Cloudflare Workers (CDN global) |

### 🎯 Decisiones conscientes que limitan capacidades

> Estas no son "limitaciones a resolver". Son **decisiones diseñadas
> para optimizar otra cosa**.

- 🏛️ **Monolito modular** en vez de microservicios → optimizamos mantenibilidad y simplicidad operativa sobre escalabilidad horizontal
- 🚪 **API Gateway** en vez de BaaS directo → optimizamos seguridad y uniformidad sobre velocidad de iteración inicial
- 🛡️ **TS strict + ESLint estricto** → ralentiza la escritura pero captura errores que costarían días depurar
- 🔺 **Pirámide de testing con pocos E2E** → optimizamos velocidad de feedback

---

## 🚀 Mejoras técnicas

### 📅 Corto plazo (1–2 sprints)

| Mejora | Por qué |
|---|---|
| 📧 **Email para notificaciones críticas** con Resend | Punto de integración natural en `AlertMatcher.notify_matching_alerts()` |
| 🪨 **Refactor de `admin.chollos.tsx`** en sub-componentes | Mejora la mantenibilidad. Estimación: 1 sprint con tests previos |
| ✅ **Marcado individual de notificaciones** | Endpoint `PATCH /v1/notifications/{id}/read` |

### 📆 Medio plazo

| Mejora | Valor |
|---|---|
| 🔔 **PWA con Service Worker + push** | App instalable, recibir push del navegador |
| 🧠 **Búsqueda semántica con embeddings** | Matching de alertas avanzado (sinónimos, intención) |
| 🏪 **Vista de tienda** (`/tienda/{slug}`) | Logo + descripción + lista de chollos por tienda |
| 🏆 **Sistema de niveles / reputación** | Para usuarios activos (votos útiles, comentarios apreciados) |
| 💬 **Webhook a Discord** además de Telegram | Canales alternativos |

### 🌅 Largo plazo

| Mejora | Cuándo aplicar |
|---|---|
| 📱 **App móvil nativa** con React Native + Expo | Reutiliza hooks de TanStack Query y servicios API existentes |
| 👥 **Multi-administrador** con panel de gestión de roles | Si crece el proyecto y entra un equipo |
| 🌍 **Internacionalización** (`i18next`) | Para mercados de habla inglesa o italiana |
| 🛒 **Mercado abierto de propuestas** | Los usuarios proponen chollos que entran en cola de revisión del admin |

---

## 🛡️ Mejoras de seguridad

| Mejora | Estado actual | Por qué no se hace ya |
|---|---|---|
| 🔐 **2FA TOTP para administradores en código** | Configuración externa: Supabase admin tiene 2FA en su cuenta personal | Para single admin con cuenta única, es proporcional |
| 🍪 **Migración JWT a cookies HttpOnly** | localStorage (default Supabase SDK) | Alto coste, SDK no lo soporta idiomáticamente, mitigado con CSP |
| 🤖 **DAST automatizado con OWASP ZAP** | Manual via `securityheaders.com` y `ssllabs.com/ssltest` | Coste CI alto sin valor añadido al tamaño actual |
| 📜 **SBOM con CycloneDX** | Lockfiles + Dependabot | Para un TFM con un solo repo, lockfiles son SBOM funcional |
| 🛡️ **WAF / Cloudflare front** | Reverse proxy DSM con HTTPS | Depende del dominio definitivo |
| 🔁 **Rotación periódica de claves** | Procedimiento documentado | Manual hoy, automatizable con scripts |
| 📦 **Política de retención de logs Sentry** | Default 30 días en plan gratuito | Suficiente para forensic básico |
| 📦 **Política de retención de `admin_audit_log`** | Indefinida en BD | Si crece, particionar por mes o archivar a S3 |

---

## ⚡ Mejoras de rendimiento

| Mejora | Estado | Cuándo aplicar |
|---|---|---|
| 📦 **Cache de respuestas Amazon Creators** | Sin cache | Si el admin pasa de 1/min a 10+/min consistentemente |
| 🤖 **Cache de respuestas OpenAI** (mismo título → mismo copy) | Sin cache | Igual |
| 🌐 **CDN para imágenes** | Servidas desde Supabase Storage | Cuando se mueva al dominio definitivo |
| 📄 **Paginación cursor-based** | Offset/limit | Si supera 10.000 chollos publicados |
| 🔁 **Server-side caching con Redis** | Sin cache | Si los endpoints públicos sufren bajo carga |
| 📦 **Compresión gzip/brotli en reverse proxy** | Por defecto en DSM | Verificar al pre-go-live |
| 🖼️ **Image optimization** (WebP, responsive) | Original sin optimizar | Cuando se ponga CDN delante |
| 📊 **Lighthouse-CI automatizado** | Métricas documentadas pero no automatizadas | Si se entrega a usuarios externos con SLAs |

### 🎯 Performance budget

| Métrica | Objetivo |
|---|---|
| 🚀 **LCP** | < 2.5s en 3G fast |
| 📐 **CLS** | < 0.1 |
| 🖱️ **INP** | < 200ms |
| 📦 **Bundle inicial gzip** | < 250 KB |

---

## 🧪 Mejoras de testing

| Mejora | Beneficio |
|---|---|
| 🐘 **Tests E2E con backend real** en CI | Levantar Postgres con GitHub Actions services. Coste: ~30s extra |
| 📷 **Visual regression** con `toHaveScreenshot` sobre páginas estables (`/login`, `/error`) | Hoy aplazado por brittleness |
| 🧬 **Mutation testing** con `mutmut` o `cosmic-ray` | Valida que los tests CORE son robustos |
| 🎲 **Property-based testing** con `hypothesis` | Para funciones de cálculo (`calculateDiscount`, `slugify`) |
| 🎭 **Page Object Model elaborado** | Cuando los E2E pasen de 20 |

---

## 📚 Mejoras de documentación

- 📊 **Diagramas de secuencia** para flujos críticos (creación de chollo con autocomplete, match de alerta con notificación)
- 🏗️ **Diagramas C4** (Context, Container, Component, Code) en `04-arquitectura`
- 🎬 **Vídeos cortos de demo** del proyecto (Loom) enlazados desde el `README.md`
- 🌐 **OpenAPI documentación pública** si el backend pasa a ser API pública
- 📝 **Changelog formal** además del `PROJECT_STATUS.md` (con `git-cliff` o similar)

---

## 🌟 Posible evolución del producto

Si BuenCholloTech sale del ámbito académico y se convierte en producto
real, los pasos naturales:

```
1. 🌐 Comprar dominio + configurar Cloudflare (CDN + DNS + DDoS)
        │
        ▼
2. 💎 Migrar a Supabase plan Pro (audit logs ampliados, PITR, soporte)
        │
        ▼
3. 📊 Añadir analytics (Plausible o Umami autohospedado)
        │
        ▼
4. 🛒 Sistema de afiliados ampliado (PCComponentes, MediaMarkt, Aliexpress)
        │
        ▼
5. 📧 Newsletter semanal con resumen automatizado
        │
        ▼
6. 🏆 Sistema de premios al usuario (badges, ranking)
        │
        ▼
7. 📱 App móvil + push notifications
        │
        ▼
8. 👥 Multi-administrador con panel de moderación
        │
        ▼
9. 💰 Monetización (banner discreto, afiliados ampliados, Premium)
```

> 💡 Estas son **ideas, no compromisos**. El proyecto cierra para TFM
> con el MVP funcional descrito; cualquier evolución posterior será
> decisión deliberada con su propio análisis de viabilidad.

---

<p align="center">
  <a href="08-uso-de-ia-en-el-desarrollo.md">← Anterior: Uso de IA</a> ·
  <a href="00-index.md">Índice</a> ·
  <a href="10-conclusiones.md">Siguiente: Conclusiones →</a>
</p>
