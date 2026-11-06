---
title: "Catálogo permanente: los chollos no se borran (Fase 1)"
category: "architecture"
date: "2026-11-06"
status: "active"
---

# Catálogo permanente (ADR-017)

- **Visión de Pedro (2026-11-04/05):** pasar de chollos temporales a un catálogo grande y
  multitienda. Los anuncios se mantienen; cada día se actualiza el precio; si vuelve a estar
  rebajado se avisa al **canal Admin** de Telegram (nunca al oficial; Pedro decide si lo
  reenvía) y la web lo reactiva **sin aprobación**; si sube, solo deja de estar en oferta.
  Solo se elimina lo que lleva mucho sin disponibilidad (30 días), y si el producto está en
  otras tiendas solo se quita esa tienda.
- Fase 1 hecha en `develop` el 2026-11-06 (módulo `catalog`, migración `20261105120000`,
  `price_check` diaria). Fases siguientes de la visión: ficha `/producto` multitienda y otras
  afiliaciones (2), histórico y alertas de precio solo donde la fuente lo permita (3),
  rankings/Top 10 editoriales (4), monetización (5).
- **Amazon:** no guardar histórico de precios ni hacer alertas de bajada por producto con
  datos de Amazon sin revisar la licencia (Associates/Creators API, Keepa). Solo precio
  vigente, mostrado como actual si tiene ≤ 24 h.
- **Lecciones de la prueba real:** la Creators API da 429 si se pasa de ~1 petición/s y un
  id no-ASIN tumba el lote entero con 400; el descuento que informa Amazon es frente a su
  referencia y no prueba una bajada (reactivar por él convertía subidas en «vuelve a estar
  en oferta»).
- Trabajar `develop` en un clon/worktree local (`C:\Users\fadwe\dev\bct-develop`), nunca
  cambiando de rama en el share del NAS (TD-31). Relacionado: [[project_entorno_local_pruebas]].
- **2026-11-06, petición de Pedro:** cada publicación de Telegram queda registrada
  (`telegram_publications`, panel y programados). Al reactivarse o bajar de precio
  (≥ 5 %), el canal Admin recibe el aviso y después la última publicación con el precio
  corregido, lista para reenviar. La bajada se mide contra el último aviso; nunca mueve
  `offer_price`.
- **Telegram en local/tests:** solo lo apaga `TELEGRAM_ENABLED=false`. Vaciar las variables
  no sirve (PowerShell las borra y `Settings` lee el `.env` real); así se enviaron avisos
  reales al canal Admin el 05-06/11.
