---
title: "Motor de IA unificado con OmniRoute, fallback gratuito y base para Chatbot web"
category: "architecture"
date: "2026-08-12"
status: "active"
---

# Motor de IA Unificado (OmniRoute / OpenCode / Fallback modelos gratuitos)

- **Decisión**: [ADR-013](../../docs/adr/ADR-013-motor-ia-unificado-omniroute-modelos-gratuitos.md).
- **Problema resuelto**: Eliminada la dependencia y coste de OpenAI API para tareas deterministas de preview de Amazon (`products`) y publicaciones de Telegram (`telegram`).
- **Módulo**: `buenchollo-api/app/modules/ai/`
  - `domain/`: Entidades (`AIProductEnrichment`, `AIChatMessage`, `AIChatResponse`, `LLMGenerationResult`) y puertos (`LLMClientProtocol`, `ProductEnricherProtocol`, `TelegramAIServiceProtocol`, `DealRecommenderProtocol`).
  - `infrastructure/`:
    - `llm_client.py`: `OpenAICompatibleLLMClient` con soporte para cualquier endpoint OpenAI-compatible (**OmniRoute** en `http://127.0.0.1:20128/v1` o Docker en el NAS, **OpenCode**, **Groq**, **OpenRouter**, **Ollama**), **fallback multi-modelo en cascada** (ante 429/timeout) y **parser JSON tolerante** (`extract_json_payload`).
    - `product_enricher.py`: `ProductAIEnricher` para copy (eslogan, markdown web, telegram text) y categorización.
    - `telegram_ai_service.py`: `TelegramAIService` para selección de 1-2 hashtags validados contra el catálogo.
    - `deal_recommender.py`: `DealRecommenderAssistant` motor conversacional base para el futuro **Chatbot de recomendación web**.
- **Variables de entorno**: `AI_PROVIDER`, `AI_BASE_URL`, `AI_MODEL`, `AI_FALLBACK_MODELS`, `AI_API_KEY`, `AI_TEMPERATURE`, `AI_TIMEOUT_SECONDS` (con fallback transparente a `OPENAI_API_KEY` si no se configuran).
- **Despliegue OmniRoute**: Recomendado como contenedor Docker en el NAS Synology (`20128:20128`, imagen `diegosouzapw/omniroute:latest`) con volumen persistente en `/root/.omniroute`.
- **Tests**: `app/tests/test_ai_llm_client.py` (13 tests unitarios en verde) + 14 tests de regresión de preview en verde.

## Validación local (2026-08-15)

Ver [`PROJECT_STATUS.md § 3.terdecies`](../../PROJECT_STATUS.md) para el relato
completo (incidente "Antigravity" + bug de entorno). Resumen accionable:

- **Verificado con logs reales del backend** (no solo config): las llamadas van a
  `http://192.168.1.3:20128/v1/chat/completions` (OmniRoute real en el NAS), cero a
  `api.openai.com`.
- **El fallback a OpenAI NO es failover en caliente**: `effective_ai_base_url`
  (`config.py`) solo elige `api.openai.com` si `AI_BASE_URL` está vacío al arrancar.
  Si OmniRoute cae con `AI_BASE_URL` relleno, `AI_FALLBACK_MODELS` reintenta otros
  modelos pero **contra el mismo OmniRoute caído** (mismo cliente/`base_url`
  cacheado en `OpenAICompatibleLLMClient`). Si se quiere failover real de proveedor,
  hay que implementarlo explícitamente — no existe hoy.
- **Cuidado con la latencia en cascadas de 2+ llamadas**: `ProductAIEnricher.enrich_product()`
  hacía copywriting + categorización en secuencia (20-45s con modelos gratuitos),
  superando el timeout de 15s de `apiClient`. Se paralelizó con `ThreadPoolExecutor`
  (~14s) y además se subió el timeout de esa ruta concreta a 45s
  (`productsApi.previewFromUrl`). Patrón a repetir si se añaden más llamadas de IA
  encadenadas: paralelizar primero lo independiente, timeout por ruta después.
- **Requisito de entorno para probar en local**: ver [`project_entorno_local_nas_drive.md`](project_entorno_local_nas_drive.md)
  — arrancar `buenchollo-web` siempre desde `Z:`, no `N:`.
