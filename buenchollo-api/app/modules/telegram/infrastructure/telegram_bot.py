"""Cliente de la Bot API de Telegram: envío de mensajes y fotos a canales."""

import json
import logging
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

from app.core.ssrf import resolves_to_private_ip

logger = logging.getLogger(__name__)

_BASE = "https://api.telegram.org/bot{token}/{method}"

# Límite de Telegram para fotos subidas por multipart.
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_REDIRECTS = 3


class TelegramBot:
    def __init__(self, token: str, default_chat_id: str = "") -> None:
        self._token = token
        self._default_chat_id = default_chat_id
        self.last_error: str | None = None
        # message_id del último envío correcto (para registrar la publicación).
        self.last_message_id: int | None = None

    def _url(self, method: str) -> str:
        return _BASE.format(token=self._token, method=method)

    def _redact(self, value: object) -> str:
        """Texto de un error sin el token del bot.

        Las excepciones de `requests` incluyen la URL de la petición
        (`.../bot<TOKEN>/sendMessage`): nunca deben llegar a logs, Sentry ni
        a `last_error` (que se devuelve al panel admin) con el token dentro.
        """
        text = str(value)
        return text.replace(self._token, "<token>") if self._token else text

    def _resolve_chat(self, chat_id: str | None) -> str:
        resolved = chat_id or self._default_chat_id
        if not resolved:
            raise ValueError("chat_id no especificado y no hay canal por defecto configurado.")
        return resolved

    @staticmethod
    def _message_id(resp) -> int | None:
        try:
            return int(resp.json()["result"]["message_id"])
        except Exception:
            return None

    @staticmethod
    def _extract_error(resp: requests.Response) -> str:
        try:
            data = resp.json()
            desc = data.get("description")
            if desc:
                return f"Telegram error {resp.status_code}: {desc}"
        except ValueError:
            pass  # cuerpo no JSON: se devuelve el texto en bruto
        return f"HTTP {resp.status_code}: {resp.text[:200]}"

    @staticmethod
    def _is_downloadable(url: str) -> bool:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.hostname) and not resolves_to_private_ip(url)

    @classmethod
    def _download_image(cls, url: str) -> tuple[bytes, str] | None:
        """Descarga la imagen con cabeceras de navegador para subirla como binario a Telegram.
        Evita que Telegram falle con 'failed to get HTTP URL content' en CDNs con protección.

        Defensa SSRF: cada salto de redirección se valida (sin IPs internas) y la
        descarga se corta al superar el límite de Telegram. Si no se puede, el
        caller cae al envío por URL, que descarga Telegram desde sus servidores.
        """
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        }
        current = url
        try:
            for _ in range(MAX_IMAGE_REDIRECTS + 1):
                if not cls._is_downloadable(current):
                    logger.warning("Imagen para Telegram rechazada: destino no permitido")
                    return None
                with requests.get(
                    current, headers=headers, timeout=12, stream=True, allow_redirects=False
                ) as resp:
                    if resp.is_redirect:
                        current = urljoin(current, resp.headers.get("location", ""))
                        continue
                    if not resp.ok:
                        return None
                    content = bytearray()
                    for chunk in resp.iter_content(64 * 1024):
                        content.extend(chunk)
                        if len(content) > MAX_IMAGE_BYTES:
                            logger.warning("Imagen para Telegram demasiado grande; se envía por URL")
                            return None
                    if not content:
                        return None
                    content_type = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
                    return bytes(content), content_type
        except Exception as exc:
            logger.warning("No se pudo pre-descargar la imagen %s para Telegram: %s", url, exc)
        return None

    def _send_photo(
        self,
        chat: str,
        image_url: str,
        caption: str,
        entities: list[dict] | None = None,
        parse_mode: str | None = None,
    ) -> bool:
        """Envía una foto a Telegram priorizando upload binario multipart (resiliente a bloqueos de CDN)."""
        self.last_error = None

        # 1. Intentar descargar y enviar como multipart/form-data (upload directo)
        downloaded = self._download_image(image_url)
        if downloaded:
            content, content_type = downloaded
            ext = "jpg"
            if "png" in content_type:
                ext = "png"
            elif "webp" in content_type:
                ext = "webp"

            data: dict[str, Any] = {"chat_id": chat, "caption": caption}
            if entities is not None:
                data["caption_entities"] = json.dumps(entities)
            elif parse_mode:
                data["parse_mode"] = parse_mode

            files = {"photo": (f"image.{ext}", content, content_type)}
            try:
                resp = requests.post(self._url("sendPhoto"), data=data, files=files, timeout=30)
                if resp.ok:
                    self.last_message_id = self._message_id(resp)
                    return True
                self.last_error = self._extract_error(resp)
                logger.warning("Telegram sendPhoto con archivo multipart falló: %s", self.last_error)
            except Exception as exc:
                self.last_error = f"Excepción en envío multipart: {self._redact(exc)}"
                logger.warning("Excepción en Telegram sendPhoto multipart: %s", self.last_error)

        # 2. Fallback: enviar la URL directamente a la Bot API
        try:
            payload: dict[str, Any] = {
                "chat_id": chat,
                "photo": image_url,
                "caption": caption,
            }
            if entities is not None:
                payload["caption_entities"] = entities
            elif parse_mode:
                payload["parse_mode"] = parse_mode

            resp = requests.post(self._url("sendPhoto"), json=payload, timeout=25)
            if resp.ok:
                self.last_error = None
                self.last_message_id = self._message_id(resp)
                return True
            self.last_error = self._extract_error(resp)
            logger.error("Telegram sendPhoto con URL falló: %s", self.last_error)
            return False
        except Exception as exc:
            self.last_error = f"Excepción en envío por URL: {self._redact(exc)}"
            logger.error("Telegram sendPhoto con URL falló: %s", self.last_error)
            return False

    # ── Envío de post formateado (panel Telegram) ──────────────────────────────

    def send_preformatted(
        self,
        text: str,
        entities: list[dict],
        image_url: str | None = None,
        chat_id: str | None = None,
    ) -> bool:
        """
        Envía un mensaje pre-formateado con Custom Emojis Premium vía entities.
        Si se proporciona image_url, usa sendPhoto con caption; si no, sendMessage.
        """
        self.last_error = None
        self.last_message_id = None
        chat = self._resolve_chat(chat_id)
        if image_url:
            return self._send_photo(chat=chat, image_url=image_url, caption=text, entities=entities)

        try:
            resp = requests.post(
                self._url("sendMessage"),
                json={
                    "chat_id": chat,
                    "text": text,
                    "entities": entities,
                    "disable_web_page_preview": False,
                },
                timeout=20,
            )
            if resp.ok:
                self.last_message_id = self._message_id(resp)
                return True
            self.last_error = self._extract_error(resp)
            logger.error("Telegram sendMessage falló: %s", self.last_error)
            return False
        except Exception as exc:
            self.last_error = self._redact(exc)
            logger.error("Telegram send_preformatted falló: %s", self.last_error)
            return False

    # ── Envío rápido (checkbox "publicar al guardar") ─────────────────────────

    def send_deal(
        self,
        title: str,
        current_price: float,
        affiliate_url: str,
        previous_price: float | None = None,
        discount_percentage: int | None = None,
        short_description: str | None = None,
        image_url: str | None = None,
        public_url: str | None = None,
        chat_id: str | None = None,
    ) -> bool:
        """Envío rápido en MarkdownV2 para el checkbox de 'publicar al guardar'."""
        self.last_error = None
        chat = self._resolve_chat(chat_id)

        price_line = f"💰 *{current_price}€*"
        if previous_price:
            price_line += f" ~~{previous_price}€~~"
        if discount_percentage:
            price_line += f" (\\-{discount_percentage}%)"

        lines = [f"🔥 *{self._escape(title)}*", "", price_line]
        if short_description:
            lines += ["", f"_{self._escape(short_description)}_"]

        link = public_url or affiliate_url
        lines += ["", f"[Ver chollo]({link})"]
        caption = "\n".join(lines)

        if image_url:
            return self._send_photo(chat=chat, image_url=image_url, caption=caption, parse_mode="MarkdownV2")

        try:
            resp = requests.post(
                self._url("sendMessage"),
                json={"chat_id": chat, "text": caption, "parse_mode": "MarkdownV2"},
                timeout=10,
            )
            if resp.ok:
                return True
            self.last_error = self._extract_error(resp)
            logger.error("Telegram send_deal sendMessage falló: %s", self.last_error)
            return False
        except Exception as exc:
            self.last_error = self._redact(exc)
            logger.error("Telegram send_deal falló: %s", self.last_error)
            return False

    def send_admin_notification(self, text: str, chat_id: str | None = None) -> bool:
        chat = self._resolve_chat(chat_id)
        try:
            resp = requests.post(
                self._url("sendMessage"),
                json={"chat_id": chat, "text": text, "disable_web_page_preview": True},
                timeout=10,
            )
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error("Telegram send_admin_notification falló: %s", self._redact(exc))
            return False

    @staticmethod
    def _escape(text: str) -> str:
        """Escapa caracteres reservados de MarkdownV2."""
        for ch in r"_*[]()~`>#+-=|{}.!\\":
            text = text.replace(ch, f"\\{ch}")
        return text
