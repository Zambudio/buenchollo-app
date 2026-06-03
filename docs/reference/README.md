# Referencias técnicas — BuenCholloTech

Documentos técnicos densos que no son ni operativa diaria del
repositorio (eso vive en [`../project/`](../project/00-index.md)) ni
documentación formal de defensa académica (eso vive en
[`../master/`](../master/00-index.md)), pero que mantienen valor como
referencia técnica y se enlazan desde ambos bloques.

## Documentos

| Documento | Contenido | Estado |
|---|---|---|
| [`PLAN_ARQUITECTURA.md`](PLAN_ARQUITECTURA.md) | Plan vivo del sprint de hardening arquitectónico F1–F7 con las 30 tareas completadas | ✅ Cerrado · referencia histórica |
| [`SECURITY_AUDIT.md`](SECURITY_AUDIT.md) | Auditoría OWASP Top 10 completa con 10 hallazgos priorizados (SEC-01 a SEC-10) y plan de fix detallado | ✅ Resuelto en sprint S1–S7 |
| [`SMOKE_TEST.md`](SMOKE_TEST.md) | Checklist manual exhaustivo pre-release (10 secciones · ~50 puntos) | ✅ Vigente · ejecutar antes de cada tag |

## Cuándo consultar cada documento

- **`PLAN_ARQUITECTURA.md`** — Si quieres entender cómo se llevó al
  proyecto al estado actual (sprint completo de hardening), o si
  vas a planificar un sprint similar en otro proyecto y quieres ver
  cómo se estructuró.

- **`SECURITY_AUDIT.md`** — Si vas a hacer una auditoría OWASP de tu
  propio proyecto, este sirve como **plantilla extensa** con el
  formato de cada hallazgo (severidad · categoría · archivos ·
  evidencia · riesgo · cómo se explota · impacto · recomendación ·
  cambio mínimo · validación). También es el insumo del que se
  destila [`../master/07-seguridad.md`](../master/07-seguridad.md)
  para la defensa académica.

- **`SMOKE_TEST.md`** — **Antes de cada release**. Es el checklist
  que cubre los flujos críticos que los tests E2E automatizados no
  pueden cubrir (interacciones con OAuth de Google real, publicación
  a Telegram con copy generado, audit log post-acción, etc.).

## Por qué este directorio existe

La documentación operativa de [`../project/`](../project/00-index.md)
debe ser **corta y directa**: comandos, ejemplos, tabla de errores
comunes. La documentación académica de
[`../master/`](../master/00-index.md) debe ser **explicativa y
justificativa**: por qué se tomó cada decisión.

Pero algunos documentos técnicos son **largos y densos sin caber en
ninguno de los dos modos**: una auditoría OWASP detallada de 500
líneas no es operativa diaria ni es el formato académico final. Vive
aquí, en `reference/`, y se enlaza desde donde corresponda.
