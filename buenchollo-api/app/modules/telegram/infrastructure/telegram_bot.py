import logging
import requests

logger = logging.getLogger(__name__)

_BASE = "https://api.telegram.org/bot{token}/{method}"


class TelegramBot:
    def __init__(self, token: str, chat_id: str):
        self._token = token
        self._chat_id = chat_id

    def _url(self, method: str) -> str:
        return _BASE.format(token=self._token, method=method)

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
    ) -> bool:
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
                    json={"chat_id": self._chat_id, "photo": image_url, "caption": caption, "parse_mode": "MarkdownV2"},
                    timeout=10,
                )
            else:
                resp = requests.post(
                    self._url("sendMessage"),
                    json={"chat_id": self._chat_id, "text": caption, "parse_mode": "MarkdownV2"},
                    timeout=10,
                )
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error("Telegram send failed: %s", exc)
            return False

    @staticmethod
    def _escape(text: str) -> str:
        """Escapa caracteres reservados de MarkdownV2."""
        for ch in r"_*[]()~`>#+-=|{}.!\\":
            text = text.replace(ch, f"\\{ch}")
        return text
