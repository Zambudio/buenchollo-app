---
name: project_estado_2026-06
description: "Estado a 2026-06; web en producción en buenchollotech.com (Cloudflare Workers + Tunnel), hardening completo, flujo main/develop."
metadata: 
  node_type: memory
  type: project
  originSessionId: 1126b10b-ffa1-4fb6-855d-3105e06fde72
---

**Producción viva (2026-06-14):** web pública en `https://buenchollotech.com`. Frontend = TanStack Start (SSR) desplegado como **Cloudflare Worker** `buenchollotech` (Workers Builds conectado al repo `Zambudio/buenchollo-app`, rama de prod = `main`, deploy en cada push). API FastAPI en el **NAS Synology**, expuesta en `https://api.buenchollotech.com` vía **Cloudflare Tunnel** (contenedor `cloudflared` en el docker-compose; sin abrir puertos, sin DDNS). `APP_ENV=production`, CORS cerrado al dominio. Dominio en Cloudflare Registrar. Login Google (Supabase) OK.

**Hardening Cloudflare COMPLETO** (T1–T8): túnel, TLS Full(strict)+HSTS, redirect www→raíz, WAF + rate limiting + Bot Fight Mode. Guía operativa viva: **`docs/guides/Cloudflare.md`** (movida ahí en la limpieza de docs; antes en la raíz). MIGRATIONS.md también en `docs/guides/`.

**Forma de trabajo:** `main` = producción, `develop` = pruebas (push genera preview en Cloudflare). Repo estandarizado en **npm**. CI (GitHub Actions) de `main` en verde; el `npm audit` del CI bloquea en `critical` (los HIGH restantes son tooling de build esbuild/vite vía @tanstack, sin impacto en runtime). Dependabot configurado para **ignorar saltos de versión mayor**.

**Deuda técnica (no urgente):** arreglar `config.py` para aceptar `CORS_ORIGINS` por comas (hoy exige JSON array o peta); Telegram aún en Supabase Functions (migrar a `POST /telegram/notify`); deuda ADR-002 (4 rutas). Ver [[feedback_deps_solo_en_develop]] y [[feedback_forma_trabajo_iterativa]].
