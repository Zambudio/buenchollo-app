---
name: feedback_deps_solo_en_develop
description: Cambios de dependencias/framework solo en develop con CI verde antes de tocar main; no rushear a producción.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 1126b10b-ffa1-4fb6-855d-3105e06fde72
---

Los bumps de dependencias o framework (y en general cambios con riesgo de romper el build) van **solo en `develop`**, y solo se mergean a `main` **cuando el CI está en verde**. Nunca empujar a `main` "para ir rápido" sin verificar.

**Why:** un bump de `@tanstack/react-start` empujado a `main` rompió Frontend/E2E en CI (el `package-lock` quedó inconsistente para el `npm ci` de Linux), aunque en local pasaba. Hubo que revertir. `main` = producción y se despliega automáticamente, así que un cambio sin verificar afecta a la web en vivo.

**How to apply:** ante cualquier cambio de deps/build, hacerlo en `develop`, esperar CI verde, y solo entonces merge a `main`. Para fallos de `npm audit` por tooling de build, preferir ajustar el umbral (p.ej. `--audit-level=critical`) o mover el tooling a devDependencies, no bumps arriesgados. Relacionado con [[feedback_forma_trabajo_iterativa]], [[feedback_no_continuar_con_critico]] y [[project_estado_2026-06]].
