# 🎯 02 · Objetivos y alcance

> **TL;DR** · BuenCholloTech busca ser **un producto personal real**
> simultáneamente al servir como **Trabajo Final del Máster**. No se
> entrega un prototipo desechable: se entrega un sistema en producción
> con decisiones explicadas, calidad medible y seguridad aplicada.

---

## 🥇 Objetivo general

```
┌────────────────────────────────────────────────────────────┐
│                                                            │
│    Construir una plataforma web completa de comunidad      │
│    de ofertas tecnológicas que sirva simultáneamente       │
│    como producto personal en producción                    │
│    y como soporte para demostrar los contenidos del        │
│    Máster en Desarrollo con IA 2025.                       │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

El objetivo **no** es entregar un prototipo desechable, sino un
sistema:

- 🔍 **Defendible técnicamente** — cada decisión está explicada.
- 📊 **Con niveles de calidad y seguridad medibles** — no afirmaciones vagas.
- 🛠️ **Que se pueda mantener y evolucionar** — porque seguirá vivo después de la entrega.

---

## 🎯 Objetivos específicos

### 🎓 Académicos

<table>
<thead>
<tr><th>#</th><th>Objetivo</th><th>Cómo se materializa</th></tr>
</thead>
<tbody>
<tr><td>1</td><td><strong>📐 Aplicar una arquitectura razonada y documentada</strong></td><td>Monolito modular con Clean Architecture pragmática · 9 ADRs firmados</td></tr>
<tr><td>2</td><td><strong>🧪 Implementar una estrategia de calidad medible</strong></td><td>Pirámide unit/integration/E2E · coverage estratégico 100/80/0 · quality gates automáticos</td></tr>
<tr><td>3</td><td><strong>🛡️ Aplicar Security by Design y Security by Default</strong></td><td>Auditoría OWASP Top 10 completa · hallazgos priorizados · mitigaciones efectivas</td></tr>
<tr><td>4</td><td><strong>🤖 Usar IA como apoyo supervisado al desarrollo</strong></td><td>Claude Code con <code>CLAUDE.md</code> · auditorías por módulo · validación obligatoria por tests + revisión humana</td></tr>
<tr><td>5</td><td><strong>📖 Documentar las decisiones</strong></td><td>El documento que estás leyendo — y toda la carpeta <code>docs/</code></td></tr>
</tbody>
</table>

### 🚀 De producto

<table>
<thead>
<tr><th>#</th><th>Objetivo</th><th>Estado actual</th></tr>
</thead>
<tbody>
<tr><td>6</td><td><strong>🌐 Tener una plataforma en producción</strong> sirviendo a usuarios reales</td><td>✅ Desplegada en NAS Synology con DDNS HTTPS</td></tr>
<tr><td>7</td><td><strong>⚡ Automatizar el flujo manual</strong> de publicación</td><td>✅ Pega URL → autocomplete + IA en menos de 30s</td></tr>
<tr><td>8</td><td><strong>🌱 Permitir crecimiento futuro</strong> sin reescribir el núcleo</td><td>✅ Protocols + Clean Architecture facilitan extensión sin tocar el core</td></tr>
</tbody>
</table>

---

## 📦 Alcance funcional

### ✅ Lo que incluye el MVP

#### 👤 Para usuarios anónimos

- Navegación pública del feed de chollos (home con scroll infinito, populares, búsqueda, detalle)
- Acceso al canal de Telegram desde la web
- Click en el enlace afiliado (Amazon Associates)
- 📈 Gráfica de precios histórica (Keepa) en el detalle

#### 🔑 Para usuarios registrados (Google OAuth)

Todo lo anterior, más:

- 👍 Votar chollos (sistema de temperatura tipo Chollometro)
- 💬 Comentar con hilos
- ❤️ Marcar favoritos
- 🔔 **Crear alertas personalizadas** por keyword, categoría, tienda, marca, precio o descuento mínimo
- 📬 Recibir notificaciones in-app cuando un chollo nuevo coincida con una alerta activa

#### 🛠️ Para administradores

- 📊 Dashboard con KPIs (chollos totales, activos, usuarios, favoritos, alertas, comentarios)
- ✏️ **CRUD completo** de chollos, categorías y tiendas
- 🤖 **Autocomplete desde URL de Amazon**: extracción ASIN + Amazon Creators API + OpenAI genera copy
- 🔁 **Detector de duplicados por ASIN** con diálogo de "sobrescribir" / "ir al existente"
- 📤 Publicación a Telegram con copy adaptado por IA
- 🗒️ Audit log de todas las acciones críticas

---

### 🔭 Lo que NO incluye el MVP

> Documentado en detalle en
> [`09 · Limitaciones y mejoras futuras`](09-limitaciones-y-mejoras-futuras.md).

- 📧 Notificaciones por email (modelo `notify_email` preparado)
- 👥 Múltiples administradores
- 🔍 Búsqueda semántica con embeddings
- 📱 App móvil nativa
- 🌍 Internacionalización (web sólo en español)
- 🔐 2FA TOTP en código (queda como configuración externa en Supabase)
- 🛡️ DAST automatizado con OWASP ZAP

---

## ⚙️ Alcance técnico

### 🧱 Stack

```
┌────────────────────────────────────────────────────────────┐
│  FRONTEND                                                  │
│  React 19 · TypeScript strict · Vite · TanStack Router    │
│  TanStack Query · Tailwind · shadcn/ui                    │
├────────────────────────────────────────────────────────────┤
│  BACKEND                                                   │
│  Python 3.11 · FastAPI 0.136 · SQLAlchemy 2 async         │
│  asyncpg · Pydantic v2                                    │
├────────────────────────────────────────────────────────────┤
│  PERSISTENCIA & AUTH                                       │
│  PostgreSQL (Supabase managed) · RLS en 12 tablas         │
│  Supabase Auth (Google OAuth + email)                     │
│  Supabase Storage (imágenes admin)                        │
├────────────────────────────────────────────────────────────┤
│  INTEGRACIONES EXTERNAS                                    │
│  Amazon Creators API · OpenAI GPT-4o                      │
│  Telegram Bot API · Sentry SaaS                           │
├────────────────────────────────────────────────────────────┤
│  DEPLOY                                                    │
│  NAS Synology DSM 7.2+ · Docker Compose                   │
│  Reverse proxy DSM · Let's Encrypt                        │
├────────────────────────────────────────────────────────────┤
│  CI/CD                                                     │
│  GitHub Actions (4 jobs) · Husky · Dependabot semanal     │
└────────────────────────────────────────────────────────────┘
```

### 🎯 Justificaciones rápidas

| Capa | Por qué este stack |
|---|---|
| **TS strict + Pydantic strict** | Detección temprana de errores en frontera entre cliente y servidor |
| **TanStack Router file-based** | Type-safe navigation, organización clara |
| **TanStack Query** | Elimina el `useEffect + setState` manual y caché de fetch |
| **FastAPI async + asyncpg** | Async-first, OpenAPI auto-generado |
| **Supabase managed** | Auth + Storage + Postgres en un único proveedor; backups incluidos |
| **NAS Synology** | Coste cero de hosting; control total |
| **GitHub Actions + Husky** | Quality gates antes de pushear y antes de mergear |

Justificaciones detalladas: [`docs/adr/`](../adr/00-index.md).

---

## 🏁 ¿Qué se considera "terminado"?

El proyecto se entrega cuando se cumplen estas 8 condiciones,
**todas presentes en el repositorio en el momento de la entrega**:

| # | Condición | Estado |
|---|---|---|
| 1 | CI verde en `main` con los 4 jobs | ✅ |
| 2 | **167 tests automatizados** verdes | ✅ |
| 3 | Coverage threshold automatizado en `src/lib/**` ≥ 90% | ✅ |
| 4 | **0 CVEs** conocidas en deps de producción | ✅ |
| 5 | **9 ADRs** firmados cubriendo las decisiones clave | ✅ |
| 6 | Documentación dual (operativa + académica) coherente | ✅ |
| 7 | Plataforma **desplegada y accesible** en el NAS | ✅ |
| 8 | Tag de release **`v1.0.0-tfm`** publicado | ✅ |

---

<p align="center">
  <a href="01-introduccion-del-proyecto.md">← Anterior: Introducción</a> ·
  <a href="00-index.md">Índice</a> ·
  <a href="03-analisis-funcional.md">Siguiente: Análisis funcional →</a>
</p>
