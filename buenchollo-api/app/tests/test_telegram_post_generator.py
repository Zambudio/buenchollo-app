import pytest

from app.modules.telegram.application.post_generator import TelegramPostGenerator


def test_web_link_in_telegram_post_uses_attribution_entrypoint() -> None:
    generator = TelegramPostGenerator(ai_service=object())
    text = generator.generate_text(
        title="Chollo de prueba",
        current_price=99.0,
        affiliate_url="https://www.amazon.es/dp/B0ABC12345",
    )

    link_entity = next(
        entity
        for entity in generator.build_entities(text)
        if entity["type"] == "text_link"
    )

    assert link_entity["url"] == "https://buenchollotech.com/telegram"


class _SlowAIService:
    async def generate_copy(self, title, details, provider=None):
        import asyncio

        await asyncio.sleep(1)
        return "nunca llega"


class _FastAIService:
    def __init__(self):
        self.calls = []

    async def generate_copy(self, title, details, provider=None):
        self.calls.append((title, details, provider))
        return "Copy de la IA"


@pytest.mark.asyncio
async def test_generate_copy_devuelve_none_si_la_ia_tarda_demasiado() -> None:
    generator = TelegramPostGenerator(ai_service=_SlowAIService())

    assert await generator.generate_copy("Titulo", "Detalles", timeout=0.01) is None


@pytest.mark.asyncio
async def test_generate_copy_pasa_el_motor_elegido() -> None:
    ai = _FastAIService()
    generator = TelegramPostGenerator(ai_service=ai)

    assert await generator.generate_copy("Titulo", "Detalles", provider="auto") == "Copy de la IA"
    assert ai.calls == [("Titulo", "Detalles", "auto")]
