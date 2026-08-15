---
title: "Entorno local en unidad de red duplicada (N:/Z:) e incidente de otra IA ('Antigravity')"
category: "environment"
date: "2026-08-15"
status: "active"
---

# Entorno local: unidad de red duplicada + incidente con otro agente de IA

- **Contexto físico**: el repo vive en una unidad de red del NAS
  (`\\Zambu-nas\nas-drive-pedro`) que la máquina de trabajo tiene mapeada por
  **dos letras de unidad distintas a la vez**: `N:` y `Z:`. Confirmar con
  `Get-PSDrive -PSProvider FileSystem | Select-Object Name, DisplayRoot`.
- **Síntoma**: arrancar `buenchollo-web` (`npm run dev`) desde `N:` hace que
  Vite/TanStack Start mezclen rutas `N:` y `Z:` para el mismo módulo
  internamente. Resultado: `Cannot GET /` en toda ruta, sin ningún error en
  consola ni en el log del servidor (el middleware SSR de TanStack Start
  simplemente no llega a registrarse). Con `vite-tsconfig-paths` pasa lo
  mismo con el alias `@/*` (`Failed to run dependency scan`).
- **Fix aplicado**: arrancar siempre `buenchollo-web` desde `Z:`, no `N:`.
  Además, `vite.config.ts` ya trae un alias `@` explícito de respaldo
  (`resolve.alias`) por si `vite-tsconfig-paths` vuelve a fallar. Detalle
  completo en [`PROJECT_STATUS.md § 3.terdecies`](../../PROJECT_STATUS.md) y
  en [`docs/project/09-troubleshooting.md`](../../docs/project/09-troubleshooting.md).
- **Incidente relacionado (2026-08-15)**: otro agente de IA ("Antigravity"),
  al toparse con este mismo síntoma sin diagnosticar la causa real, pasó ~1h
  "arreglándolo" mal: convirtió el proyecto de TanStack Start (SSR) en una
  SPA manual añadiendo `appType: "spa"` a `vite.config.ts` y creando
  `index.html` + `src/main.tsx` (que no existían). La web volvía a cargar
  visualmente pero **ninguna interacción funcionaba** (dos sistemas de
  hidratación compitiendo por el DOM). Se revirtió todo con `git restore` +
  borrado de los ficheros nuevos.
- **Lección para el futuro**: si la web "carga pero no responde a nada" tras
  una sesión de otra herramienta/IA, **revisar `git status`/`git diff` antes
  de asumir que el código de la feature está roto** — puede ser un cambio de
  entorno ajeno a la tarea en curso, no un bug de la feature que se está
  probando.
