"""Unit tests for the unified AI engine (LLM client, JSON extractor, fallback, and assistants)."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.config import Settings
from app.modules.ai.domain.entities import AIChatMessage
from app.modules.ai.infrastructure.deal_recommender import DealRecommenderAssistant
from app.modules.ai.infrastructure.llm_client import (
    OpenAICompatibleLLMClient,
    extract_json_payload,
)
from app.modules.ai.infrastructure.product_enricher import ProductAIEnricher
from app.modules.ai.infrastructure.telegram_ai_service import TelegramAIService
from app.modules.products.domain.entities import ProductPreview


# ── Tests de Extracción y Sanitización de JSON ───────────────────────────────

def test_extract_json_payload_pure():
    raw = '{"category_id": "tech", "subcategory_id": "laptops"}'
    result = extract_json_payload(raw)
    assert result == {"category_id": "tech", "subcategory_id": "laptops"}


def test_extract_json_payload_markdown_codeblock():
    raw = """
    Aquí está el resultado:
    ```json
    {
        "short_description": "Super chollo",
        "long_description": "Detalles completos"
    }
    ```
    Espero que te sirva.
    """
    result = extract_json_payload(raw)
    assert result is not None
    assert result["short_description"] == "Super chollo"
    assert result["long_description"] == "Detalles completos"


def test_extract_json_payload_with_trailing_commas():
    raw = '{"short_description": "Texto", "items": [1, 2, ], }'
    result = extract_json_payload(raw)
    assert result is not None
    assert result["short_description"] == "Texto"


def test_extract_json_payload_invalid_returns_none():
    assert extract_json_payload("No hay json aquí") is None
    assert extract_json_payload("") is None


# ── Tests de OpenAICompatibleLLMClient y Fallback en Cascada ────────────────

def test_llm_client_model_cascade():
    settings = Settings(
        ai_model="primary-free",
        ai_fallback_models=["fallback-1", "fallback-2", "primary-free"],
    )
    client = OpenAICompatibleLLMClient(settings)
    cascade = client._get_model_cascade()
    assert cascade == ["primary-free", "fallback-1", "fallback-2"]


def test_llm_client_generate_text_fallback_on_error():
    settings = Settings(
        ai_model="model-fails",
        ai_fallback_models=["model-succeeds"],
        openai_api_key="",
    )
    client = OpenAICompatibleLLMClient(settings)

    mock_sync_client = MagicMock()

    # Primer modelo falla con Exception (ej: 429), segundo modelo tiene éxito
    fail_response = Exception("Rate limit reached 429")
    ok_response = MagicMock()
    ok_response.choices = [MagicMock(message=MagicMock(content="Respuesta de respaldo"))]

    mock_sync_client.chat.completions.create.side_effect = [fail_response, ok_response]

    with patch.object(client, "_sync_client", mock_sync_client):
        result = client.generate_text([{"role": "user", "content": "Hola"}])
        assert result.content == "Respuesta de respaldo"
        assert result.model == "model-succeeds"
        assert mock_sync_client.chat.completions.create.call_count == 2


def test_llm_client_generate_text_fallback_to_openai_after_3_empty_responses():
    """Verifica que tras 3 respuestas vacías de modelos gratuitos, se enruta a OpenAI oficial."""
    settings = Settings(
        ai_model="model-empty-1",
        ai_fallback_models=["model-empty-2", "model-empty-3", "model-extra"],
        openai_api_key="sk-test-key",
        openai_model="gpt-4o",
        ai_max_empty_responses=3,
    )
    client = OpenAICompatibleLLMClient(settings)

    mock_primary_client = MagicMock()
    empty_res = MagicMock()
    empty_res.choices = [MagicMock(message=MagicMock(content="   "))]  # Respuesta vacía
    mock_primary_client.chat.completions.create.return_value = empty_res

    mock_openai_client = MagicMock()
    openai_res = MagicMock()
    openai_res.choices = [MagicMock(message=MagicMock(content="Descripción generada por OpenAI gpt-4o"))]
    mock_openai_client.chat.completions.create.return_value = openai_res

    with patch.object(client, "_sync_client", mock_primary_client), \
         patch.object(client, "_openai_sync_client", mock_openai_client):

        result = client.generate_text([{"role": "user", "content": "Genera post"}])

        assert result.content == "Descripción generada por OpenAI gpt-4o"
        assert result.model == "openai/gpt-4o"
        # Debe haber intentado exactamente 3 veces con modelos gratuitos antes de saltar a OpenAI
        assert mock_primary_client.chat.completions.create.call_count == 3
        assert mock_openai_client.chat.completions.create.call_count == 1


def test_llm_client_generate_json_fallback_to_openai_after_failures():
    """Verifica que si los modelos gratuitos fallan o devuelven JSON vacío, se enruta a OpenAI."""
    settings = Settings(
        ai_model="model-fails-json",
        ai_fallback_models=["model-fails-2", "model-fails-3"],
        openai_api_key="sk-test-key",
        openai_model="gpt-4o-mini",
        ai_max_empty_responses=3,
    )
    client = OpenAICompatibleLLMClient(settings)

    mock_primary_client = MagicMock()
    mock_primary_client.chat.completions.create.side_effect = Exception("OmniRoute 502 Bad Gateway")

    mock_openai_client = MagicMock()
    openai_res = MagicMock()
    openai_res.choices = [MagicMock(message=MagicMock(content='{"short_description": "Chollo", "telegram_text": "Texto telegram"}'))]
    mock_openai_client.chat.completions.create.return_value = openai_res

    with patch.object(client, "_sync_client", mock_primary_client), \
         patch.object(client, "_openai_sync_client", mock_openai_client):

        result = client.generate_json([{"role": "user", "content": "Genera JSON"}])

        assert result["short_description"] == "Chollo"
        assert result["telegram_text"] == "Texto telegram"
        assert mock_openai_client.chat.completions.create.call_count == 1


@pytest.mark.asyncio
async def test_llm_client_agenerate_text_fallback_to_openai():
    """Verifica fallback asíncrono a OpenAI tras fallos en modelos gratuitos."""
    settings = Settings(
        ai_model="async-fails",
        ai_fallback_models=["async-fails-2"],
        openai_api_key="sk-test-key",
        openai_model="gpt-4o",
        ai_max_empty_responses=2,
    )
    client = OpenAICompatibleLLMClient(settings)

    mock_primary_async = MagicMock()
    mock_primary_async.chat.completions.create = AsyncMock(side_effect=Exception("Connection refused"))

    mock_openai_async = MagicMock()
    openai_res = MagicMock()
    openai_res.choices = [MagicMock(message=MagicMock(content="Async OpenAI response"))]
    mock_openai_async.chat.completions.create = AsyncMock(return_value=openai_res)

    with patch.object(client, "_async_client", mock_primary_async), \
         patch.object(client, "_openai_async_client", mock_openai_async):

        res = await client.agenerate_text([{"role": "user", "content": "Ping"}])
        assert res.content == "Async OpenAI response"
        assert res.model == "openai/gpt-4o"


def test_llm_client_generate_json_fallback():
    settings = Settings(
        ai_model="model-fails-json",
        ai_fallback_models=["model-good-json"],
        openai_api_key="",
    )
    client = OpenAICompatibleLLMClient(settings)
    mock_sync_client = MagicMock()

    # Primer modelo devuelve texto no json, segundo devuelve json válido
    bad_res = MagicMock()
    bad_res.choices = [MagicMock(message=MagicMock(content="Texto sin estructura"))]

    good_res = MagicMock()
    good_res.choices = [MagicMock(message=MagicMock(content='{"status": "ok"}'))]

    mock_sync_client.chat.completions.create.side_effect = [bad_res, good_res]

    with patch.object(client, "_sync_client", mock_sync_client):
        result = client.generate_json([{"role": "user", "content": "Genera JSON"}])
        assert result == {"status": "ok"}


@pytest.mark.asyncio
async def test_llm_client_agenerate_text_success():
    settings = Settings(ai_model="model-async")
    client = OpenAICompatibleLLMClient(settings)
    mock_async_client = MagicMock()

    ok_res = MagicMock()
    ok_res.choices = [MagicMock(message=MagicMock(content="Async content"))]
    mock_async_client.chat.completions.create = AsyncMock(return_value=ok_res)

    with patch.object(client, "_async_client", mock_async_client):
        res = await client.agenerate_text([{"role": "user", "content": "Ping"}])
        assert res.content == "Async content"
        assert res.model == "model-async"


# ── Tests de ProductAIEnricher ───────────────────────────────────────────────

def test_product_ai_enricher_full():
    mock_llm = MagicMock()
    mock_llm.generate_json.side_effect = [
        # 1. Copywriting call
        {
            "short_description": "Eslogan potente",
            "long_description": "**Gran oferta** de producto",
            "telegram_text": "Chollo en canal",
        },
        # 2. Categorization call
        {
            "category_id": "informatica",
            "subcategory_id": "portatiles",
        },
    ]

    enricher = ProductAIEnricher(mock_llm)
    product = ProductPreview(
        title="Portátil Gaming RTX 4060",
        description="Pantalla 144Hz, 16GB RAM, 512GB SSD",
    )

    data = enricher.enrich_product(product, "informatica | Informática")

    assert data["short_description"] == "Eslogan potente"
    assert data["long_description"] == "**Gran oferta** de producto"
    assert data["telegram_text"] == "Chollo en canal"
    assert data["category_id"] == "informatica"
    assert data["subcategory_id"] == "portatiles"


def test_product_ai_enricher_graceful_error_handling():
    mock_llm = MagicMock()
    mock_llm.generate_json.side_effect = Exception("Router down")

    enricher = ProductAIEnricher(mock_llm)
    product = ProductPreview(title="Test Product")
    data = enricher.enrich_product(product, "cat")

    assert "⚠️ Error IA" in data["short_description"]
    assert "Hubo un error" in data["long_description"]


# ── Tests de TelegramAIService ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_telegram_ai_service_suggest_categories():
    mock_llm = MagicMock()
    res = MagicMock()
    res.content = "#gaming #portatiles #otraCosaNoEnLista"
    mock_llm.agenerate_text = AsyncMock(return_value=res)

    service = TelegramAIService(mock_llm)
    suggested = await service.suggest_categories(
        title="Portátil MSI",
        description="Portátil para jugar",
        available=["#gaming", "#portatiles", "#hogar", "#ropa"],
    )

    assert suggested == ["#gaming", "#portatiles"]


@pytest.mark.asyncio
async def test_telegram_ai_service_empty_available():
    mock_llm = MagicMock()
    service = TelegramAIService(mock_llm)
    suggested = await service.suggest_categories("Titulo", "Desc", [])
    assert suggested == []


# ── Tests de DealRecommenderAssistant (Chatbot Web) ─────────────────────────

@pytest.mark.asyncio
async def test_deal_recommender_assistant_chat():
    mock_llm = MagicMock()
    res = MagicMock()
    res.content = "Te recomiendo este monitor LG UltraGear de 144Hz que está por 150€."
    res.model = "deepseek-chat-free"
    mock_llm.agenerate_text = AsyncMock(return_value=res)

    assistant = DealRecommenderAssistant(mock_llm)
    messages = [
        AIChatMessage(role="user", content="Busco un buen monitor gaming barato"),
    ]
    deals_context = [
        {"id": "deal-1", "title": "Monitor LG UltraGear", "current_price": 150.0, "discount_percentage": 30},
    ]

    response = await assistant.chat(messages, deals_context)

    assert "LG UltraGear" in response.content
    assert response.model_used == "deepseek-chat-free"
    assert len(response.suggested_deals) == 1
    assert response.suggested_deals[0]["id"] == "deal-1"
