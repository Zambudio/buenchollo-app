"""Capturador de correo para el entorno local (sustituto de Mailpit).

La API local envía los emails aquí en vez de a Zoho: nada sale a Internet.
  - SMTP en 127.0.0.1:1025 con STARTTLS (certificado autofirmado generado al
    vuelo) y AUTH que acepta cualquier credencial, porque el emisor SMTP de
    la API siempre hace starttls() + login() fuera del puerto 465.
  - Web en http://localhost:8025 para leer los correos.
  - JSON en /api/messages (lo usan las pruebas automáticas) y
    POST /api/clear para vaciar el buzón.

Mailpit no se usa porque Windows App Control bloquea su binario sin firmar.
"""

from __future__ import annotations

import argparse
import datetime as dt
import email
import email.policy
import html
import json
import ssl
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from aiosmtpd.controller import Controller
from aiosmtpd.smtp import AuthResult
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from common import RUNTIME_DIR

MAIL_DIR = RUNTIME_DIR / "mail"
MESSAGES_DIR = MAIL_DIR / "messages"


def _tls_context() -> ssl.SSLContext:
    cert_path, key_path = MAIL_DIR / "cert.pem", MAIL_DIR / "key.pem"
    if not cert_path.exists():
        key = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
        now = dt.datetime.now(dt.timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - dt.timedelta(days=1))
            .not_valid_after(now + dt.timedelta(days=3650))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
            .sign(key, hashes.SHA256())
        )
        key_path.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ctx.load_cert_chain(cert_path, key_path)
    return ctx


class _Handler:
    async def handle_DATA(self, server, session, envelope):
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        path = MESSAGES_DIR / f"{stamp}_{uuid.uuid4().hex[:8]}.eml"
        path.write_bytes(envelope.original_content or envelope.content)
        msg = email.message_from_bytes(path.read_bytes(), policy=email.policy.default)
        print(f"[mail] {msg['To']} ← {msg['Subject']}", flush=True)
        return "250 Message accepted for delivery"


def _accept_any(server, session, envelope, mechanism, auth_data):
    return AuthResult(success=True)


def _parse(path: Path) -> dict:
    msg = email.message_from_bytes(path.read_bytes(), policy=email.policy.default)
    html_part = msg.get_body(preferencelist=("html",))
    text_part = msg.get_body(preferencelist=("plain",))
    return {
        "id": path.stem,
        "date": msg["Date"],
        "from": msg["From"],
        "to": msg["To"],
        "subject": msg["Subject"],
        "html": html_part.get_content() if html_part else "",
        "text": text_part.get_content() if text_part else "",
    }


def _messages() -> list[Path]:
    return sorted(MESSAGES_DIR.glob("*.eml"), reverse=True)


class _Web(BaseHTTPRequestHandler):
    def log_message(self, *args):  # silencio: el log del capturador es el de SMTP
        pass

    def _send(self, status: int, body: str, ctype: str = "text/html; charset=utf-8") -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/messages":
            return self._send(200, json.dumps([_parse(p) for p in _messages()]), "application/json")
        if self.path.startswith("/m/"):
            path = MESSAGES_DIR / f"{Path(self.path[3:]).name}.eml"
            if not path.exists():
                return self._send(404, "No encontrado")
            m = _parse(path)
            body = m["html"] or f"<pre>{html.escape(m['text'])}</pre>"
            return self._send(200, _page(
                f"<p><a href='/'>← Bandeja</a></p><h2>{html.escape(m['subject'] or '')}</h2>"
                f"<p><b>De:</b> {html.escape(m['from'] or '')}<br><b>Para:</b> {html.escape(m['to'] or '')}"
                f"<br><b>Fecha:</b> {html.escape(m['date'] or '')}</p>"
                f"<iframe sandbox srcdoc=\"{html.escape(body)}\" "
                "style='width:100%;height:75vh;border:1px solid #ccc'></iframe>"
            ))
        if self.path == "/":
            rows = "".join(
                f"<tr><td>{html.escape(m['date'] or '')}</td><td>{html.escape(m['to'] or '')}</td>"
                f"<td><a href='/m/{m['id']}'>{html.escape(m['subject'] or '(sin asunto)')}</a></td></tr>"
                for m in map(_parse, _messages())
            )
            return self._send(200, _page(
                "<h1>Correo local · BuenChollo</h1>"
                "<form method='post' action='/api/clear'><button>Vaciar bandeja</button></form>"
                f"<table><tr><th>Fecha</th><th>Para</th><th>Asunto</th></tr>{rows}</table>"
                "<script>setTimeout(()=>location.reload(),5000)</script>"
            ))
        return self._send(404, "No encontrado")

    def do_POST(self):
        if self.path == "/api/clear":
            for p in _messages():
                p.unlink(missing_ok=True)
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
            return None
        return self._send(404, "No encontrado")


def _page(inner: str) -> str:
    return (
        "<!doctype html><meta charset='utf-8'><title>Correo local</title>"
        "<style>body{font-family:system-ui;margin:2rem}table{border-collapse:collapse;width:100%}"
        "td,th{border-bottom:1px solid #ddd;padding:.4rem;text-align:left}</style>" + inner
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smtp-port", type=int, default=1025)
    parser.add_argument("--web-port", type=int, default=8025)
    args = parser.parse_args()

    MESSAGES_DIR.mkdir(parents=True, exist_ok=True)
    controller = Controller(
        _Handler(),
        hostname="127.0.0.1",
        port=args.smtp_port,
        tls_context=_tls_context(),
        authenticator=_accept_any,
        auth_require_tls=True,
    )
    controller.start()
    print(f"[mail] SMTP en 127.0.0.1:{args.smtp_port} · web en http://localhost:{args.web_port}", flush=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.web_port), _Web)
    try:
        server.serve_forever()
    finally:
        controller.stop()


if __name__ == "__main__":
    main()
