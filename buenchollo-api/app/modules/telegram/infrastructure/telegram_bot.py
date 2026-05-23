"""Cliente de la Bot API de Telegram: envío de mensajes y fotos a canales."""

import logging
import requests

logger = logging.getLogger(__name__)

_BASE = "https://api.telegram.org/bot{token}/{method}"


class TelegramBot:
    def __init__(self, token: str, default_chat_id: str = "") -> None:
        self._token = token
        self._default_chat_id = default_chat_id

    def _url(self, method: str) -> str:
        return _BASE.format(token=self._token, method=method)

    def _resolve_chat(self, chat_id: str | None) -> str:
        resolved = chat_id or self._default_chat_id
        if not resolved:
            raise ValueError("chat_id no especificado y no hay canal por defecto configurado.")
        return resolved

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
        chat = self._resolve_chat(chat_id)
        try:
            if image_url:
                resp = requests.post(
                    self._url("sendPhoto"),
                    json={
                        "chat_id": chat,
                        "photo": image_url,
                        "caption": text,
                        "caption_entities": entities,
                    },
                    timeout=25,
                )
            else:
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
            resp.raise_for_status()
            return True
        except Exception:
            logger.exception("Telegram send_preformatted falló")
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

        try:
            if image_url:
                resp = requests.post(
                    self._url("sendPhoto"),
                    json={"chat_id": chat, "photo": image_url, "caption": caption, "parse_mode": "MarkdownV2"},
                    timeout=10,
                )
            else:
                resp = requests.post(
                    self._url("sendMessage"),
                    json={"chat_id": chat, "text": caption, "parse_mode": "MarkdownV2"},
                    timeout=10,
                )
            resp.raise_for_status()
            return True
        except Exception:
            logger.exception("Telegram send_deal falló")
            return False

    @staticmethod
    def _escape(text: str) -> str:
        """Escapa caracteres reservados de MarkdownV2."""
        for ch in r"_*[]()~`>#+-=|{}.!\\":
            text = text.replace(ch, f"\\{ch}")
        return text
