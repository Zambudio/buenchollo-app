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
