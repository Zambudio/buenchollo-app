"""Job del scheduler (cada 2 min) que publica en la página de Facebook la cola
`facebook_posts`.

Si hay algo pendiente, pide el token de la página con el del usuario del
sistema (`FACEBOOK_ACCESS_TOKEN`) y sube cada foto con su texto. Los fallos se
reintentan en los siguientes pasos (hasta 5 intentos y 24 h); después queda en
error y se avisa al administrador.

Si Facebook no responde al publicar, el post pudo salir: se da por publicado y
se avisa para revisarlo, en vez de arriesgar un duplicado. Un token inválido o
sin permisos para la cola y avisa (como mucho cada 12 h).
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from app.core import events
from app.core.config import Settings
from app.core.jobs import job_session
from app.modules.facebook.domain.models import POST_ERROR, POST_PUBLISHED, FacebookPost
from app.modules.facebook.infrastructure.graph_client import FacebookApiError, FacebookGraphClient
from app.modules.facebook.infrastructure.repository import FacebookRepository

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
MAX_AGE = timedelta(hours=24)
ALERT_EVERY = timedelta(hours=12)

# Último aviso de token (el scheduler es un proceso largo; al reiniciar, como
# mucho un aviso de más).
_last_token_alert: datetime | None = None


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


class _TokenInvalid(Exception):
    pass


class FacebookPublisher:
    def __init__(
        self,
        session,
        repo: FacebookRepository,
        settings: Settings,
        *,
        client_factory: Callable[..., FacebookGraphClient] = FacebookGraphClient,
        # Para tests; None → evento AdminAlert.
        notify: Callable[[str], object] | None = None,
    ):
        self.session = session
        self.repo = repo
        self.settings = settings
        self.client_factory = client_factory
        self.notify = notify

    async def run(self, now: datetime | None = None) -> int:
        """Publica lo pendiente; devuelve cuántas publicaciones salieron."""
        s = self.settings
        if not s.facebook_enabled:
            return 0
        token, page_id = (s.facebook_access_token or "").strip(), (s.facebook_page_id or "").strip()
        if not token or not page_id:
            logger.info("Facebook activado sin FACEBOOK_ACCESS_TOKEN o FACEBOOK_PAGE_ID; no se publica")
            return 0
        now = now or datetime.now(timezone.utc)
        pending = await self.repo.pending_ids()
        if not pending:
            return 0

        client = self.client_factory(token, s.facebook_graph_version)
        try:
            page = await asyncio.to_thread(client.page_access, page_id)
        except FacebookApiError as exc:
            if exc.token_invalid or not exc.transient:
                await self._token_problem(str(exc), now)
            else:
                logger.warning("Facebook: no se pudo obtener el token de la página (%s); se reintenta", exc)
            return 0

        published = 0
        for post_id in pending:
            try:
                post = await self.repo.lock_pending(post_id)
                if post is not None:
                    published += await self._publish_one(post, client, page_id, page.access_token, now)
                await self.session.commit()
            except _TokenInvalid as exc:
                await self.session.commit()  # guarda el intento antes de parar
                await self._token_problem(str(exc), now)
                break
            except Exception:
                logger.exception("Facebook: error de BD con la publicación %s", post_id)
                await self.session.rollback()
        return published

    async def _publish_one(self, post: FacebookPost, client, page_id: str, page_token: str, now: datetime) -> int:
        if now - _aware(post.created_at) > MAX_AGE or post.attempts >= MAX_ATTEMPTS or not post.image:
            post.last_error = post.last_error or "Caducada sin publicarse"
            await self._fail(post)
            return 0
        try:
            post_ref = await asyncio.to_thread(client.publish_photo, page_id, page_token, post.image, post.message)
            self._published(post, post_ref or None, now)
            return 1
        except FacebookApiError as exc:
            if exc.unknown:
                self._published(post, None, now)
                post.last_error = "Facebook no confirmó la publicación (tiempo agotado); se da por publicada"
                await self._notify(f"⚠️ Facebook no confirmó una publicación; revisa la página. {post.message[:80]}")
                return 1
            post.attempts += 1
            post.last_error = str(exc)[:500]
            if exc.token_invalid:
                raise _TokenInvalid(str(exc)) from None
            logger.warning("Facebook: intento %d fallido para %s: %s", post.attempts, post.id, exc)
            if post.attempts >= MAX_ATTEMPTS:
                await self._fail(post)
            return 0

    @staticmethod
    def _published(post: FacebookPost, post_ref: str | None, now: datetime) -> None:
        post.status = POST_PUBLISHED
        post.post_id = post_ref
        post.published_at = now
        post.image = None
        post.last_error = None

    async def _fail(self, post: FacebookPost) -> None:
        post.status = POST_ERROR
        post.image = None
        title = post.message.split("\n", 1)[0][:100]
        logger.error("Facebook: publicación %s descartada: %s", post.id, post.last_error)
        await self._notify(f"⚠️ No se pudo publicar en Facebook: {title}. {(post.last_error or 'caducada')[:200]}")

    async def _token_problem(self, detail: str, now: datetime) -> None:
        global _last_token_alert
        logger.error("Facebook: token no válido o sin acceso a la página: %s", detail)
        if _last_token_alert is None or now - _last_token_alert >= ALERT_EVERY:
            _last_token_alert = now
            await self._notify(
                "⚠️ Facebook: no se puede publicar en la página (token caducado, revocado o sin permisos). "
                f"Genera un token nuevo y ponlo en FACEBOOK_ACCESS_TOKEN. Detalle: {detail[:200]}"
            )

    async def _notify(self, text: str) -> None:
        try:
            if self.notify is None:
                await events.publish(events.AdminAlert(text))
            else:
                result = self.notify(text)
                if inspect.isawaitable(result):
                    await result
        except Exception:
            logger.warning("Facebook: no se pudo avisar al administrador", exc_info=True)


async def _run(settings: Settings) -> int:
    if not settings.facebook_enabled or not settings.database_url:
        return 0
    async with job_session(settings) as session:
        try:
            return await FacebookPublisher(session, FacebookRepository(session), settings).run()
        except Exception:
            await session.rollback()
            logger.exception("Fallo global del job de Facebook")
            return 0


def run_facebook_queue(settings: Settings) -> int:
    """Job síncrono para APScheduler. Con FACEBOOK_ENABLED=false no hace nada."""
    return asyncio.run(_run(settings))
