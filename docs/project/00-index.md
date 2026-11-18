# 🛠️ Operativa del repositorio — BuenCholloTech

<p align="center">
  <strong>Documentación práctica para instalar, ejecutar y mantener el proyecto</strong>
</p>

---

> 📖 **¿Qué encontrarás aquí?**
> Trece capítulos numerados con **comandos**, **ejemplos** y **tablas de errores comunes**.
> Las decisiones de arquitectura (el **por qué**) viven en [`docs/adr/`](../adr/00-index.md) y los
> runbooks operativos en [`docs/guides/`](../guides/README.md).

---

## 🚀 Lectura sugerida según lo que vengas a hacer

| Vengo a... | Lee... |
|---|---|
| 🌅 **Entender qué es el proyecto** | [01](01-overview.md) |
| 📥 **Instalarlo desde cero** | [02](02-installation-and-setup.md) |
| 🧭 **Entender la estructura para tocar código** | [03](03-project-structure.md) |
| ⚙️ **Saber qué variables de entorno hay** | [04](04-configuration.md) |
| 💻 **Trabajar día a día** (commits, ramas, IA) | [05](05-development-workflow.md) |
| 🧪 **Ejecutar tests o pasar el CI** | [06](06-testing-and-quality.md) |
| 🖥️ **Probar la web en local antes de desplegar** | [`LOCAL-ENV.md`](../guides/LOCAL-ENV.md) |
| 🛡️ **Revisar la seguridad operativa** | [07](07-security.md) |
| 🚀 **Desplegar o mantener producción** | [08](08-deployment.md) |
| 🔍 **Algo no funciona** | [09](09-troubleshooting.md) |
| 🧾 **Ver qué deuda técnica queda pendiente** | [10](10-technical-debt.md) |
| ✅ **Comprobar el estado real actual** | [11](11-current-state.md) |
| 🔍 **Ver la auditoría técnica completa (2026-11)** | [12](12-auditoria-tecnica-2026-11.md) |
| 🔎 **Entender y mantener el SEO y la visibilidad en buscadores con IA** | [13](13-seo.md) |

---

## 📚 Índice completo

| # | Capítulo | Tema |
|---|---|---|
| [01](01-overview.md) | 🌅 **Overview** | Qué es, problema que resuelve, módulos, roles, flujo |
| [02](02-installation-and-setup.md) | 📥 **Instalación y setup** | Clonado, backend, frontend, Supabase, servicios externos |
| [03](03-project-structure.md) | 🗂️ **Estructura del proyecto** | Monorepo, Clean Architecture, organización por features, UI System |
| [04](04-configuration.md) | ⚙️ **Configuración** | Variables de entorno (backend, frontend, CI) |
| [05](05-development-workflow.md) | 💻 **Flujo de desarrollo** | Husky, commits, ramas, uso de IA |
| [06](06-testing-and-quality.md) | 🧪 **Testing y calidad** | Comandos, gates, coverage, métricas |
| [07](07-security.md) | 🛡️ **Seguridad** | Controles, hallazgos OWASP, política `--no-verify`, incidentes |
| [08](08-deployment.md) | 🚀 **Despliegue** | Workers, Tunnel y Docker en NAS, rollback |
| [09](09-troubleshooting.md) | 🔍 **Troubleshooting** | Errores comunes y soluciones |
| [10](10-technical-debt.md) | 🧾 **Deuda técnica** | Registro vivo de tareas pendientes |
| [11](11-current-state.md) | ✅ **Estado actual verificado** | Producción, funcionalidad, módulos, calidad y pendientes |
| [12](12-auditoria-tecnica-2026-11.md) | 🔍 **Auditoría técnica 2026-11** | Revisión completa de arquitectura, seguridad, calidad, testing y operación, con plan de acción |
| [13](13-seo.md) | 🔎 **SEO y búsqueda con IA** | Auditoría SEO, datos estructurados, `llms.txt`, sitemap, rendimiento y cómo mantenerlo |

---

## 🧭 Documentación complementaria

| Dónde | Para qué |
|---|---|
| [`../adr/`](../adr/00-index.md) | 📋 **19 ADRs** firmados y datados (decisiones arquitectónicas) |
| [`../guides/`](../guides/README.md) | 🔐 Runbooks vigentes: [LOCAL-ENV](../guides/LOCAL-ENV.md), [NAS-SSH](../guides/NAS-SSH.md), [Cloudflare](../guides/Cloudflare.md), [MIGRATIONS](../guides/MIGRATIONS.md), [SMOKE-TEST](../guides/SMOKE-TEST.md), [AFFILIATE-NETWORKS](../guides/AFFILIATE-NETWORKS.md) y [AFFILIATE-ACTIVATION-RUNBOOK](../guides/AFFILIATE-ACTIVATION-RUNBOOK.md) |
| [`../../PROJECT_STATUS.md`](../../PROJECT_STATUS.md) | 🗒️ Bitácora cronológica de cambios |
| [`../../CONTEXT.md`](../../CONTEXT.md) | 📖 Glosario del dominio (chollo, tienda, visita, sesión...) |
| [`../../PRODUCT.md`](../../PRODUCT.md) | 🎯 Contexto de producto y diseño (usuarios, posicionamiento, principios) |
| [`../../SECURITY.md`](../../SECURITY.md) | 🛡️ Política de divulgación responsable |

---

<p align="center">
  <em>Repositorio: <a href="https://github.com/Zambudio/buenchollo-app">github.com/Zambudio/buenchollo-app</a></em>
</p>
