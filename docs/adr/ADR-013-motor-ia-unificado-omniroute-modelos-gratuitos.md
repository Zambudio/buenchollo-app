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

3. **Sistema de Fallback Multi-Modelo en Cascada**:
   - Si el modelo gratuito principal devuelve un error `429 Too Many Requests` (límite de cuota/rate limit), `503 Service Unavailable`, timeout o contenido vacío, el cliente reintenta de forma automática y secuencial con los modelos de respaldo definidos en `AI_FALLBACK_MODELS`.

4. **Parser JSON Defensivo (`extract_json_payload`)**:
   - Capa de sanitización que extrae JSON válido incluso cuando los modelos devuelven bloques markdown (\`\`\`json ... \`\`\`), texto conversacional extra o comas finales (trailing commas).

5. **Base para Chatbot de Recomendación Web (`DealRecommenderAssistant`)**:
   - Asistente conversacional desacoplado que recibe el historial de chat e inyecta contexto de ofertas activas para generar recomendaciones personalizadas.

6. **Retrocompatibilidad Transparente**:
   - `OpenAIAssistant` en `products` se mantiene como fachada adaptadora para evitar roturas en código heredado.
   - Si no se definen las variables `AI_*` pero existe `OPENAI_API_KEY`, el sistema continúa funcionando sin errores.

---

## 3. Consecuencias y Beneficios

- **Coste cero en operaciones rutinarias**: Las tareas automáticas de Telegram y preview de Amazon operan sobre modelos gratuitos sin saldo de OpenAI.
- **Alta disponibilidad**: La rotación de fallback previene fallos por saturación de cuota gratuita de un modelo individual.
- **Desacoplamiento total**: Cambiar de proveedor o modelo se realiza mediante variables de entorno (`AI_BASE_URL`, `AI_MODEL`), sin tocar código de dominio ni casos de uso.
- **Chatbot web listo para conectar**: El servicio conversacional queda preparado para la interfaz de frontend.
