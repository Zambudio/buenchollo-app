# 🧾 10 · Deuda técnica

> **TL;DR** · Registro vivo de lo que falta o conviene mejorar **ahora mismo**.
> Solo items **abiertos**: cuando uno se cierra, se elimina de aquí (el histórico
> resuelto vive en [`PROJECT_STATUS.md`](../../PROJECT_STATUS.md)). Para consultar el diseño de arquitectura, ver [`docs/master/`](../master/00-index.md).

Última revisión: **2026-08-29** (Cierre de TD-15, TD-16 y TD-17 — ver `PROJECT_STATUS.md` § 3.sexdecies).

---

## 🟡 Media — mejora de mantenibilidad

- **TD-18 — Vigilar la regla `no_longer_deal` ahora que el modo automático está
  activado.** El usuario activó `enabled=true` (frecuencia semanal) tras
  validar el flujo manual con datos reales (89 candidatos, todo correcto). Amazon a
  veces omite `savingBasis`/`savings.percentage` en productos que siguen genuinamente
  en oferta, lo que el handler (`price_check_handler.py`) interpreta como "ya no es
  oferta" y borra — en modo automático no hay revisión humana antes del borrado (sí
  queda registro restaurable). Revisar el registro de ejecuciones tras las primeras
  corridas automáticas y comprobar qué fracción de los borrados cae en el motivo
  `no_longer_deal`; si es alta, ajustar la regla o volver a `enabled=false` hasta
  afinarla.

---

> 🔁 **Cómo usar esta página:** revisar al empezar cada tanda de trabajo. Al cerrar un
> item, borrar su entrada y anotar el cierre (fecha + commit) en `PROJECT_STATUS.md`.
