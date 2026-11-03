"""Script de prueba para enviar vistas previas de los correos a una dirección de email.

Uso:
    python scripts/send_test_email.py --type welcome
    python scripts/send_test_email.py --type alert_digest
    python scripts/send_test_email.py --type confirmation
    python scripts/send_test_email.py --type recovery
    python scripts/send_test_email.py --type submission_admin
    python scripts/send_test_email.py --type submission_approved
    python scripts/send_test_email.py --type submission_rejected
    python scripts/send_test_email.py --type all
"""
import argparse
import os
import smtplib
import sys
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.modules.emails.application.rendering import (  # noqa: E402
    EmailBranding,
    build_digest_deal,
    render_alert_digest,
    format_eur,
    render_auth_template,
    render_submission_admin,
    render_submission_approved,
    render_submission_rejected,
    render_welcome,
)


def _load_env_file() -> None:
    env_path = ROOT / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k not in os.environ:
                    os.environ[k] = v


def _send_email(to_email: str, smtp_user: str, smtp_password: str, subject: str, html: str, text: str) -> None:
    smtp_host = os.environ.get("SMTP_HOST", "smtp.zoho.eu")
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    from_name = os.environ.get("SMTP_FROM_NAME", "BuenChollo Tech")
    from_email = os.environ.get("SMTP_FROM_EMAIL", smtp_user)
    reply_to = os.environ.get("SMTP_REPLY_TO", "contacto@buenchollotech.com")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    if reply_to:
        msg["Reply-To"] = reply_to

    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

    print(f"  ✅ Enviado vía {smtp_host}:{smtp_port}: {subject}")


def get_sample_digest_deals(branding: EmailBranding) -> list:
    expires = datetime.now(timezone.utc) + timedelta(hours=14)
    deal1 = build_digest_deal(
        branding=branding,
        title="Portátil Gaming ASUS TUF A15 (Ryzen 7, 16GB, 1TB SSD, RTX 4060)",
        slug="portatil-asus-tuf-gaming-a15-rtx4060",
        image_url="https://m.media-amazon.com/images/I/71u+mKkYcGL._AC_SL1500_.jpg",
        current_price=Decimal("899.00"),
        previous_price=Decimal("1199.00"),
        discount_percentage=25,
        store_name="Amazon España",
        short_description="Mínimo histórico. Pantalla 15.6'' FHD 144Hz, teclado RGB y refrigeración optimizada.",
        expires_at=expires,
        asin="B0BSLJ4Y89",
        show_price_history=True,
        alert_names=("Portátil Gaming", "ASUS TUF"),
    )
    deal2 = build_digest_deal(
        branding=branding,
        title="Auriculares Inalámbricos Sony WH-1000XM5 con Cancelación de Ruido",
        slug="auriculares-sony-wh-1000xm5-cancelacion-ruido",
        image_url="https://m.media-amazon.com/images/I/51SKmu2G9FL._AC_SL1200_.jpg",
        current_price=Decimal("299.00"),
        previous_price=Decimal("379.00"),
        discount_percentage=21,
        store_name="Amazon España",
        short_description="Cancelación de ruido líder en el mercado, hasta 30h de batería y carga rápida.",
        expires_at=None,
        asin="B09Y2MYL5C",
        show_price_history=False,
        alert_names=("Auriculares",),
    )
    return [deal1, deal2]


def send_preview(email_type: str, to_email: str, smtp_user: str, smtp_password: str, name: str = "Pedro") -> None:
    branding = EmailBranding()

    if email_type == "welcome":
        rendered = render_welcome(branding, name=name)
        subject = f"[VISTA PREVIA] {rendered.subject}"
        _send_email(to_email, smtp_user, smtp_password, subject, rendered.html, rendered.text)

    elif email_type == "alert_digest":
        deals = get_sample_digest_deals(branding)
        unsubscribe_url = f"{branding.site_url}/perfil#correos?token=demo_baja_inmediata"
        rendered = render_alert_digest(
            branding,
            name=name,
            digest_date=date.today(),
            deals=deals,
            unsubscribe_url=unsubscribe_url,
        )
        subject = f"[VISTA PREVIA] {rendered.subject}"
        _send_email(to_email, smtp_user, smtp_password, subject, rendered.html, rendered.text)

    elif email_type == "confirmation":
        html = render_auth_template(
            branding,
            icon="✉️",
            eyebrow="Confirma tu cuenta",
            title="Confirma tu correo y empieza a cazar chollos",
            intro="Estás a un clic de completar tu registro en BuenChollo Tech. Pulsa el botón para confirmar tu cuenta:",
            action_url="https://buenchollotech.com/auth/confirm?token=demo_verificacion_12345",
            button_label="Confirmar mi correo",
            expiry_note="Por seguridad, el enlace caduca en 24 horas.",
            safety_note="Si no has solicitado crear una cuenta en BuenChollo Tech, ignora este mensaje: no se activará ningún servicio sin este enlace.",
        )
        subject = "[VISTA PREVIA] Confirma tu correo · BuenChollo Tech"
        _send_email(to_email, smtp_user, smtp_password, subject, html, "Confirma tu cuenta en BuenChollo Tech.")

    elif email_type == "recovery":
        html = render_auth_template(
            branding,
            icon="🔑",
            eyebrow="Recuperar acceso",
            title="Restablece tu contraseña",
            intro="Hemos recibido una solicitud para cambiar la contraseña de tu cuenta. Pulsa el botón para elegir una nueva:",
            action_url="https://buenchollotech.com/auth/reset-password?token=demo_recuperacion_67890",
            button_label="Elegir nueva contraseña",
            expiry_note="Por seguridad, el enlace caduca en 1 hora.",
            safety_note="Si no has pedido cambiar tu contraseña, puedes ignorar este correo con tranquilidad: tu contraseña actual sigue activa y nadie puede acceder sin este enlace.",
        )
        subject = "[VISTA PREVIA] Restablece tu contraseña · BuenChollo Tech"
        _send_email(to_email, smtp_user, smtp_password, subject, html, "Restablece tu contraseña en BuenChollo Tech.")

    elif email_type == "reauthentication":
        html = render_auth_template(
            branding,
            icon="🛡️",
            eyebrow="Verificación de seguridad",
            title="Confirma que eres tú",
            intro="Introduce este código de seguridad en la web para autorizar la acción que has solicitado:",
            code="842 195",
            expiry_note="El código caduca en 10 minutos.",
            safety_note="Nunca compartas este código con nadie. El equipo de BuenChollo Tech nunca te pedirá tu código por mensaje ni por correo.",
        )
        subject = "[VISTA PREVIA] Tu código de verificación · BuenChollo Tech"
        _send_email(to_email, smtp_user, smtp_password, subject, html, "Tu código de verificación es 842 195.")

    elif email_type == "submission_admin":
        rendered = render_submission_admin(
            branding,
            title="Auriculares Sony WH-1000XM5 <b>con cancelación</b> de ruido",
            price=format_eur(279),
            previous_price=format_eur(379),
            store="Amazon España",
            author=name,
            image_url="https://m.media-amazon.com/images/I/51SKmu2G9FL._AC_SL1200_.jpg",
            review_url=f"{branding.site_url}/admin/propuestas?id=00000000-0000-4000-8000-000000000000",
            warnings=["Se eliminó un enlace de afiliado ajeno", "Tienda sin afiliación"],
        )
        _send_email(to_email, smtp_user, smtp_password, f"[VISTA PREVIA] {rendered.subject}", rendered.html, rendered.text)

    elif email_type == "submission_approved":
        rendered = render_submission_approved(
            branding, name=name, title="Auriculares Sony WH-1000XM5", deal_url=f"{branding.site_url}/chollo/auriculares-sony-wh-1000xm5"
        )
        _send_email(to_email, smtp_user, smtp_password, f"[VISTA PREVIA] {rendered.subject}", rendered.html, rendered.text)

    elif email_type == "submission_rejected":
        rendered = render_submission_rejected(
            branding,
            name=name,
            title="Auriculares Sony WH-1000XM5",
            reason="El precio ya no está vigente en la tienda.",
            my_deals_url=f"{branding.site_url}/mis-chollos",
        )
        _send_email(to_email, smtp_user, smtp_password, f"[VISTA PREVIA] {rendered.subject}", rendered.html, rendered.text)

    else:
        print(f"Tipo desconocido: {email_type}")


def main() -> None:
    _load_env_file()
    parser = argparse.ArgumentParser(description="Envía correos de prueba")
    parser.add_argument("--type", default="all", choices=["all", "welcome", "alert_digest", "confirmation", "recovery", "reauthentication", "submission_admin", "submission_approved", "submission_rejected"])
    parser.add_argument("--to", default=os.environ.get("TEST_RECIPIENT", "pjzambudio@gmail.com"))
    parser.add_argument("--name", default="Pedro")
    args = parser.parse_args()

    smtp_user = os.environ.get("SMTP_USER", "info@buenchollotech.com")
    password = os.environ.get("SMTP_PASSWORD") or os.environ.get("GMAIL_APP_PASSWORD")

    if not password:
        print("❌ Error: Falta la contraseña de aplicación en el .env")
        sys.exit(1)

    print(f"Iniciando envío de pruebas a {args.to}...")
    if args.type == "all":
        types = ["alert_digest", "confirmation", "recovery", "reauthentication"]
        for t in types:
            print(f"Enviando {t}...")
            send_preview(t, args.to, smtp_user, password, name=args.name)
            time.sleep(2)
        print("\n🎉 ¡Todas las vistas previas han sido enviadas correctamente!")
    else:
        send_preview(args.type, args.to, smtp_user, password, name=args.name)


if __name__ == "__main__":
    main()
