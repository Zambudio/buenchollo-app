"""Genera las plantillas de correo de Supabase Auth con el estilo de la web.

Uso (desde buenchollo-api/):

    python scripts/build_auth_email_templates.py

Escribe `supabase/templates/<tipo>.html` y `supabase/templates/subjects.json`.
El HTML conserva las variables de Supabase (`{{ .ConfirmationURL }}`, `{{ .Token }}`,
`{{ .Email }}`, `{{ .NewEmail }}`), así que se pega tal cual en
Supabase → Authentication → Emails → Templates (o lo usa `supabase/config.toml`
en local). Ver docs/guides/Correos.md.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.modules.emails.application.rendering import EmailBranding, render_auth_template  # noqa: E402

URL = "{{ .ConfirmationURL }}"
EXPIRY = "Por seguridad, el enlace caduca en 24 horas."

TEMPLATES: dict[str, dict] = {
    "confirmation": {
        "subject": "Confirma tu correo · BuenChollo Tech",
        "icon": "✉️",
        "eyebrow": "Confirma tu cuenta",
        "title": "Confirma tu correo y empieza a cazar chollos",
        "intro": (
            "Estás a un clic de completar tu registro en BuenChollo Tech. "
            "Pulsa el botón para confirmar que este correo es tuyo."
        ),
        "action_url": URL,
        "button_label": "Confirmar mi correo",
        "expiry_note": EXPIRY,
    },
    "recovery": {
        "subject": "Restablece tu contraseña · BuenChollo Tech",
        "icon": "🔑",
        "eyebrow": "Recuperar acceso",
        "title": "Restablece tu contraseña",
        "intro": (
            "Hemos recibido una solicitud para cambiar la contraseña de tu cuenta. "
            "Pulsa el botón para elegir una nueva."
        ),
        "action_url": URL,
        "button_label": "Elegir nueva contraseña",
        "expiry_note": "Por seguridad, el enlace caduca en 1 hora.",
        "safety_note": (
            "Si no has pedido cambiar la contraseña, ignora este correo: "
            "la actual sigue funcionando y nadie puede cambiarla sin este enlace."
        ),
    },
    "email_change": {
        "subject": "Confirma tu nuevo correo · BuenChollo Tech",
        "icon": "🔄",
        "eyebrow": "Cambio de correo",
        "title": "Confirma tu nuevo correo",
        "intro": "Has pedido cambiar el correo de tu cuenta de BuenChollo Tech. Confírmalo para terminar:",
        "detail": "{{ .Email }} &nbsp;→&nbsp; <strong style=\"color:#00ebff;\">{{ .NewEmail }}</strong>",
        "action_url": URL,
        "button_label": "Confirmar cambio",
        "expiry_note": EXPIRY,
        "safety_note": (
            "Si no has pedido este cambio, no pulses el botón y cambia tu contraseña: "
            "alguien podría tener acceso a tu cuenta."
        ),
    },
    "magic_link": {
        "subject": "Tu enlace para entrar · BuenChollo Tech",
        "icon": "✨",
        "eyebrow": "Acceso sin contraseña",
        "title": "Entra en BuenChollo Tech",
        "intro": "Pulsa el botón para iniciar sesión. No hace falta contraseña.",
        "action_url": URL,
        "button_label": "Entrar ahora",
        "expiry_note": "El enlace solo funciona una vez y caduca en 1 hora.",
    },
    "reauthentication": {
        "subject": "Tu código de verificación · BuenChollo Tech",
        "icon": "🛡️",
        "eyebrow": "Verificación",
        "title": "Confirma que eres tú",
        "intro": "Introduce este código en la web para completar la acción que has solicitado:",
        "code": "{{ .Token }}",
        "expiry_note": "El código caduca en unos minutos.",
    },
    "invite": {
        "subject": "Te han invitado a BuenChollo Tech",
        "icon": "🎟️",
        "eyebrow": "Invitación",
        "title": "Te han invitado a BuenChollo Tech",
        "intro": (
            "Tienes una invitación para unirte a la comunidad que caza los mejores chollos "
            "de tecnología. Acepta para crear tu cuenta."
        ),
        "action_url": URL,
        "button_label": "Aceptar invitación",
        "expiry_note": EXPIRY,
    },
}


def main() -> None:
    out_dir = ROOT / "supabase" / "templates"
    out_dir.mkdir(parents=True, exist_ok=True)
    branding = EmailBranding()
    subjects = {}
    for name, content in TEMPLATES.items():
        html = render_auth_template(branding, **content)
        (out_dir / f"{name}.html").write_text(html, encoding="utf-8")
        subjects[name] = content["subject"]
        print(f"{name}: {len(html) / 1024:.1f} KB")
    (out_dir / "subjects.json").write_text(
        json.dumps(subjects, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
