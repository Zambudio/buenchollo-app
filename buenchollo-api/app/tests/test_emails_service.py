"""Tests unitarios del servicio de correos y plantillas."""
import asyncio
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.modules.emails.application.rendering import (
    EmailBranding,
    build_digest_deal,
    render_alert_digest,
    render_welcome,
)
from app.modules.emails.application.welcome_service import WelcomeEmailService
from app.modules.emails.domain.messages import OutgoingEmail
from app.modules.emails.infrastructure.smtp import SmtpEmailSender


def test_render_welcome_email():
    branding = EmailBranding()
    rendered = render_welcome(branding, name="Pedro")

    assert "Te damos la bienvenida a BuenChollo Tech" in rendered.subject
    assert "Pedro" in rendered.html
    assert "https://buenchollotech.com/logo-512.png" in rendered.html
    assert "https://t.me/buenchollotech" in rendered.html
    assert "Telegram" in rendered.text


def test_render_alert_digest_email():
    branding = EmailBranding()
    deal = build_digest_deal(
        branding=branding,
        title="Portátil Gaming ASUS TUF A15",
        slug="asus-tuf-a15",
        image_url="https://example.com/laptop.jpg",
        current_price=Decimal("899.00"),
        previous_price=Decimal("1199.00"),
        discount_percentage=25,
        store_name="Amazon España",
        short_description="Excelente portátil con RTX 4060",
        expires_at=None,
        asin="B0CRXXXXXX",
        show_price_history=True,
        alert_names=("Portátiles gaming",),
    )
    rendered = render_alert_digest(
        branding,
        name="Pedro",
        digest_date=date(2026, 10, 31),
        deals=[deal],
        unsubscribe_url="https://buenchollotech.com/perfil?tab=alertas",
    )

    assert "Tu alerta tiene un chollo" in rendered.subject
    assert "ASUS TUF A15" in rendered.html
    assert "899,00 €" in rendered.html
    assert "Darme de baja" in rendered.html
    assert "tab=alertas" in rendered.html


def test_smtp_sender_missing_config():
    settings = MagicMock()
    settings.smtp_host = ""
    settings.smtp_user = ""
    settings.smtp_password = ""

    sender = SmtpEmailSender(settings)
    outgoing = OutgoingEmail(
        to="test@example.com",
        subject="Test",
        html="<p>Test</p>",
        text="Test",
    )
    assert sender.send(outgoing) is False


def test_smtp_sender_success_mocked():
    settings = MagicMock()
    settings.smtp_host = "smtp.zoho.eu"
    settings.smtp_port = 465
    settings.smtp_user = "info@buenchollotech.com"
    settings.smtp_password = "secret_password"
    settings.smtp_from_name = "BuenChollo Tech"
    settings.smtp_from_email = "info@buenchollotech.com"
    settings.smtp_reply_to = "contacto@buenchollotech.com"
    settings.smtp_use_ssl = True
    settings.smtp_timeout_seconds = 5.0

    sender = SmtpEmailSender(settings)
    outgoing = OutgoingEmail(
        to="user@example.com",
        subject="Bienvenido",
        html="<p>Bienvenido</p>",
        text="Bienvenido",
    )

    with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
        instance = MagicMock()
        mock_smtp_ssl.return_value.__enter__.return_value = instance

        result = sender.send(outgoing)
        assert result is True
        instance.login.assert_called_once_with("info@buenchollotech.com", "secret_password")
        instance.send_message.assert_called_once()


def test_welcome_service_idempotence():
    async def _test():
        sender = MagicMock()
        sender.send_async = AsyncMock(return_value=True)

        supabase_mock = MagicMock()
        admin_auth = MagicMock()
        supabase_mock.auth.admin = admin_auth

        user_obj = MagicMock()
        user_obj.user_metadata = {"welcome_email_sent_at": "2026-10-31T20:00:00Z"}
        admin_auth.get_user_by_id.return_value = user_obj

        service = WelcomeEmailService(sender=sender, supabase_client=supabase_mock)
        sent = await service.send_welcome_if_needed(
            user_id="user-123",
            email="test@example.com",
            name="Pedro",
        )

        assert sent is False
        sender.send_async.assert_not_called()

    asyncio.run(_test())


def test_welcome_api_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import get_current_user, AuthenticatedUser

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id="usr-123", email="usuario@ejemplo.com"
    )

    with patch.object(WelcomeEmailService, "send_welcome_if_needed", AsyncMock(return_value=True)):
        client = TestClient(app)
        res = client.post("/v1/auth/welcome", json={"display_name": "Pedro"})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["sent"] is True

    app.dependency_overrides.clear()
