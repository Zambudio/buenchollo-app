# ADR-013: Motor de IA Unificado con Gateways OpenAI-Compatibles (OmniRoute / OpenCode) y Fallback de Modelos Gratuitos

- **Estado**: ✅ Aceptado
- **Fecha**: 2026-08-12
- **Autor**: BuenChollo Tech Team

---

## 1. Contexto y Problema

En las versiones anteriores, el backend (`buenchollo-api`) dependía de llamadas directas a la API oficial de pago de OpenAI (`gpt-4o`, `gpt-4o-mini`) para dos operaciones deterministas:
1. **Enriquecimiento y categorización de productos** (`app/modules/products`): generación de eslogan corto, descripción web en markdown, texto para Telegram y categorización de IDs.
2. **Sugerencia de hashtags para Telegram** (`app/modules/telegram`): selección de categorías del catálogo.

Además, el roadmap del proyecto incluye la incorporación de un **Chatbot interactivo en la web** para recomendar ofertas y chollos a los usuarios finales en tiempo real.

Mantener dependencias directas con proveedores de pago para estas tareas genera un coste operativo innecesario cuando existen modelos abiertos/gratuitos de alto rendimiento y gateways locales de IA como **OmniRoute** u **OpenCode**, o proveedores de capa gratuita como **Groq**, **OpenRouter** u **Ollama**.

---

## 2. Decisión Arquitectónica

1. **Creación del módulo transversal `app/modules/ai/`**:
   - Centraliza toda la interacción con Modelos de Lenguaje (LLMs).
   - Define puertos y abstracciones desacopladas (`LLMClientProtocol`, `ProductEnricherProtocol`, `TelegramAIServiceProtocol`, `DealRecommenderProtocol`).

2. **Cliente Agnóstico OpenAI-Compatible (`OpenAICompatibleLLMClient`)**:
   - Se comunica con cualquier router o endpoint compatible con la especificación OpenAI mediante `base_url` y `api_key`.
   - Se conecta por defecto al gateway local **OmniRoute** (`http://127.0.0.1:20128/v1` o alojado en contenedor Docker en el NAS).

3. **Sistema de Fallback Multi-Modelo en Cascada y Enrutamiento a OpenAI Oficial**:
   - Si el modelo gratuito principal devuelve un error `429 Too Many Requests` (límite de cuota/rate limit), `503 Service Unavailable`, `404 Not Found`, timeout o contenido vacío, el cliente prueba secuencialmente los modelos de respaldo definidos en `AI_FALLBACK_MODELS`.
   - **Umbral de fallos/vacíos (`AI_MAX_EMPTY_RESPONSES=3`)**: Si se acumulan 3 respuestas vacías o fallos consecutivos en los modelos gratuitos, el cliente interrumpe la cascada y enruta de forma automática hacia la API oficial de OpenAI (`https://api.openai.com/v1`) con `OPENAI_API_KEY` y `OPENAI_MODEL` (`gpt-4o`).
   - **Timeouts rápidos para modelos gratuitos (`fast_free_timeout = min(ai_timeout_seconds, 6.0)`, `max_retries=0`)**: Evita que peticiones colgadas en el router local bloqueen el hilo o agoten el timeout de Cloudflare (524), saltando a OpenAI oficial en milisegundos si hay errores.

4. **Parser JSON Defensivo (`extract_json_payload`) y Rescate de Datos**:
   - Capa de sanitización que extrae JSON válido incluso cuando los modelos devuelven bloques markdown (\`\`\`json ... \`\`\`), texto conversacional extra o comas finales (trailing commas).
   - En caso de fallo total del motor de IA, `ProductAIEnricher` y `TelegramPanel` utilizan fallbacks locales basados en los datos del producto (título, precio, características) para que la interfaz nunca quede en blanco.

5. **Base para Chatbot de Recomendación Web (`DealRecommenderAssistant`)**:
   - Asistente conversacional desacoplado que recibe el historial de chat e inyecta contexto de ofertas activas para generar recomendaciones personalizadas.

6. **Retrocompatibilidad Transparente**:
   - `OpenAIAssistant` en `products` se mantiene como fachada adaptadora para evitar roturas en código heredado.
   - Si no se definen las variables `AI_*` pero existe `OPENAI_API_KEY`, el sistema continúa funcionando sin errores.

---

## 3. Consecuencias y Beneficios

- **Coste cero en operaciones rutinarias cuando los modelos gratuitos están disponibles**: Las tareas automáticas de Telegram y preview de Amazon operan sobre modelos gratuitos sin saldo de OpenAI.
- **Resiliencia garantizada**: Si el router local o los modelos gratuitos fallan o devuelven texto vacío, el sistema salta de inmediato a OpenAI oficial de forma transparente y sin interrupción de servicio para el usuario.
- **Latencia controlada**: Con timeouts rápidos en la capa gratuita y sin reintentos internos duplicados, la respuesta se genera en pocos segundos.
- **Desacoplamiento total**: Cambiar de proveedor o modelo se realiza mediante variables de entorno (`AI_BASE_URL`, `AI_MODEL`), sin tocar código de dominio ni casos de uso.
- **Chatbot web listo para conectar**: El servicio conversacional queda preparado para la interfaz de frontend.
