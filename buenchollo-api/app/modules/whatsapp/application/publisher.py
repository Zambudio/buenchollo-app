"""Job del scheduler (cada minuto) que publica en el Canal de WhatsApp la cola
`whatsapp_posts` a través de la pasarela `whatsapp-gateway`.

Ritmo, para que el Canal se comporte como una persona y no como un bot:
  · como mucho una publicación por paso del job;
  · al menos `WHATSAPP_MIN_INTERVAL_MINUTES` entre dos publicaciones;
  · como mucho `WHATSAPP_DAILY_LIMIT` al día (hora de Madrid);
  · cada post espera además un margen aleatorio tras salir en Telegram (cola).
Lo que no cabe espera al siguiente hueco; a las 12 h se descarta y se avisa.

Fallos:
  · pasarela caída, WhatsApp sin vincular o mala configuración (token, Canal,
    rol) → no cuenta como intento; un aviso al canal Admin como mucho cada 6 h;
  · error al publicar → hasta 5 intentos; desde el 3.º, solo texto (si la imagen
    es lo que falla, el chollo sale igual con su enlace);
  · tiempo agotado después de enviar → se da por publicado y se avisa para
    revisarlo, en vez de arriesgar un duplicado (como en Telegram e Instagram).
"""

from __future__ import annotations

import asyncio
import inspect
import io
import logging
import re
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from PIL import Image

from app.core import events
from app.core.config import Settings
from app.core.jobs import job_session
from app.modules.whatsapp.domain.models import POST_ERROR, POST_PUBLISHED, WhatsAppPost
from app.modules.whatsapp.infrastructure.gateway_client import GatewayError, WhatsAppGatewayClient
from app.modules.whatsapp.infrastructure.repository import WhatsAppRepository

logger = logging.getLogger(__name__)

MADRID = ZoneInfo("Europe/Madrid")
MAX_ATTEMPTS = 5
TEXT_ONLY_FROM_ATTEMPT = 2  # tras 2 fallos con imagen, se publica solo el texto
MAX_AGE = timedelta(hours=12)
ALERT_EVERY = timedelta(hours=6)
ADMIN_ROLES = {"OWNER", "ADMIN"}

_JID = re.compile(r"^\d+@newsletter$")

# Estado en memoria del proceso del scheduler (vive mientras el contenedor).
# Canal resuelto y comprobado: (JID, cuándo); el rol se vuelve a mirar cada 6 h.
_resolved_jid: dict[str, tuple[str, datetime]] = {}
ROLE_RECHECK = timedelta(hours=6)
_last_alert: dict[str, datetime] = {}


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def start_of_day(now: datetime) -> datetime:
    local = now.astimezone(MADRID)
    return local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)


def invite_code(channel: str) -> str:
    """`https://whatsapp.com/channel/0029Vb…` → `0029Vb…`."""
    return channel.strip().rstrip("/").split("/")[-1].split("?")[0]


def image_size(image: bytes) -> tuple[int, int] | None:
    try:
        with Image.open(io.BytesIO(image)) as img:
            return img.size
    except Exception:
        return None


class WhatsAppPublisher:
    def __init__(
        self,
        session,
        repo: WhatsAppRepository,
        settings: Settings,
        *,
        client: WhatsAppGatewayClient | None = None,
        # Para tests; None → evento AdminAlert.
        notify: Callable[[str], object] | None = None,
    ):
        self.session = session
        self.repo = repo
        self.settings = settings
        self.client = client or WhatsAppGatewayClient(settings.whatsapp_gateway_url, settings.whatsapp_gateway_token)
        self.notify = notify

    async def run(self, now: datetime | None = None) -> int:
        """Publica como mucho una pendiente; devuelve 1 si salió."""
        if not self.settings.whatsapp_enabled:
            return 0
        now = now or datetime.now(timezone.utc)

        last = await self.repo.last_published_at()
        if last and now - _aware(last) < timedelta(minutes=max(0, self.settings.whatsapp_min_interval_minutes)):
            return 0
        if await self.repo.published_since(start_of_day(now)) >= self.settings.whatsapp_daily_limit:
            return 0

        post = await self.repo.next_due(now)
        if post is None:
            await self.session.commit()
            return 0
        try:
            published = await self._handle(post, now)
            await self.session.commit()
            return published
        except Exception:
            logger.exception("WhatsApp: error con la publicación %s", post.id)
            await self.session.rollback()
            return 0

    async def _handle(self, post: WhatsAppPost, now: datetime) -> int:
        if now - _aware(post.created_at) > MAX_AGE or post.attempts >= MAX_ATTEMPTS:
            post.last_error = post.last_error or "Caducada: no hubo hueco ni conexión en 12 h"
            await self._fail(post)
            return 0
        try:
            status = await asyncio.to_thread(self.client.status)
            if not status.connected:
                await self._offline(f"WhatsApp no está vinculado ({status.connection})", now, pairing=status.pairing_code)
                return 0
            jid = await self._channel_jid(now)
            if jid is None:
                return 0
            with_image = post.image is not None and post.attempts < TEXT_ONLY_FROM_ATTEMPT
            image = post.image if with_image else None
            size = image_size(image) if image else None
            message_id = await asyncio.to_thread(self.client.send, jid, post.text, image, size)
            dropped_image = post.image is not None and not with_image
            self._published(post, message_id, now)
            if dropped_image:
                post.last_error = "Publicada solo con texto: la imagen falló"
            return 1
        except GatewayError as exc:
            if exc.unknown:
                self._published(post, None, now)
                post.last_error = "La pasarela no confirmó la publicación (tiempo agotado); se da por publicada"
                await self._notify(f"⚠️ WhatsApp no confirmó una publicación; revisa el Canal. {self._title(post)}")
                return 1
            if exc.offline:
                await self._offline(str(exc), now)
                return 0
            if exc.config:
                await self._alert(
                    "config",
                    "⚠️ WhatsApp: la pasarela rechaza el token. WHATSAPP_GATEWAY_TOKEN debe ser el mismo "
                    "en la API y en buenchollo-whatsapp.",
                    now,
                )
                return 0
            post.attempts += 1
            post.last_error = str(exc)[:500]
            logger.warning("WhatsApp: intento %d fallido para %s: %s", post.attempts, post.id, exc)
            if post.attempts >= MAX_ATTEMPTS:
                await self._fail(post)
            return 0

    async def _channel_jid(self, now: datetime) -> str | None:
        """JID del Canal: el de `WHATSAPP_CHANNEL` si ya es un JID o, si es el
        enlace de invitación, el que devuelve la pasarela (se guarda en memoria).
        Comprueba que la cuenta vinculada administra el Canal."""
        configured = (self.settings.whatsapp_channel or "").strip()
        if not configured:
            await self._alert("config", "⚠️ WhatsApp: falta WHATSAPP_CHANNEL (enlace o JID del Canal).", now)
            return None
        cached = _resolved_jid.get(configured)
        if cached and now - cached[1] < ROLE_RECHECK:
            return cached[0]
        try:
            if _JID.match(configured):
                info = await asyncio.to_thread(self.client.channel, jid=configured)
            else:
                info = await asyncio.to_thread(self.client.channel, invite=invite_code(configured))
        except GatewayError as exc:
            if exc.offline or exc.config:
                raise
            await self._alert("config", f"⚠️ WhatsApp: no se encuentra el Canal de WHATSAPP_CHANNEL ({exc}).", now)
            return None
        role = str(info.get("role") or "").upper()
        jid = info.get("jid")
        if not jid or role not in ADMIN_ROLES:
            _resolved_jid.pop(configured, None)
            await self._alert(
                "role",
                f"⚠️ WhatsApp: la cuenta vinculada no administra el Canal «{info.get('name') or configured}» "
                f"(rol: {role or 'ninguno'}). Vincula la cuenta propietaria o hazla administradora.",
                now,
            )
            return None
        _resolved_jid[configured] = (jid, now)
        logger.info("WhatsApp: publicando en el Canal «%s» (%s) como %s", info.get("name"), jid, role)
        return jid

    async def _offline(self, detail: str, now: datetime, *, pairing: str | None = None) -> None:
        logger.warning("WhatsApp: %s", detail)
        hint = f" Código de vinculación: {pairing}." if pairing else " Vincúlalo de nuevo (ver docs/guides/WHATSAPP.md)."
        await self._alert("offline", f"⚠️ WhatsApp: no se puede publicar en el Canal. {detail}.{hint}", now)

    async def _alert(self, key: str, text: str, now: datetime) -> None:
        last = _last_alert.get(key)
        if last is None or now - last >= ALERT_EVERY:
            _last_alert[key] = now
            await self._notify(text)

    @staticmethod
    def _title(post: WhatsAppPost) -> str:
        return post.text.split("\n", 1)[0].replace("*", "")[:100]

    @staticmethod
    def _published(post: WhatsAppPost, message_id: str | None, now: datetime) -> None:
        post.status = POST_PUBLISHED
        post.message_id = message_id
        post.published_at = now
        post.image = None
        post.last_error = None

    async def _fail(self, post: WhatsAppPost) -> None:
        post.status = POST_ERROR
        post.image = None
        logger.error("WhatsApp: publicación %s descartada: %s", post.id, post.last_error)
        await self._notify(
            f"⚠️ No se pudo publicar en el Canal de WhatsApp: {self._title(post)}. {(post.last_error or '')[:200]}"
        )

    async def _notify(self, text: str) -> None:
        """Aviso al administrador por el bus (`AdminAlert`): hoy, el canal Admin de Telegram."""
        try:
            if self.notify is None:
                await events.publish(events.AdminAlert(text))
            else:
                result = self.notify(text)
                if inspect.isawaitable(result):
                    await result
        except Exception:
            logger.warning("WhatsApp: no se pudo avisar al administrador", exc_info=True)


async def _run(settings: Settings) -> int:
    if not settings.whatsapp_enabled or not settings.database_url:
        return 0
    async with job_session(settings) as session:
        try:
            return await WhatsAppPublisher(session, WhatsAppRepository(session), settings).run()
        except Exception:
            await session.rollback()
            logger.exception("Fallo global del job de WhatsApp")
            return 0


def run_whatsapp_queue(settings: Settings) -> int:
    """Job síncrono para APScheduler. Con WHATSAPP_ENABLED=false no hace nada."""
    return asyncio.run(_run(settings))
