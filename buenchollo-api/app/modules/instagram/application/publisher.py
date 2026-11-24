"""Job del scheduler (cada 2 min) que publica en el feed de Instagram la cola
`instagram_posts` y mantiene vivo el token.

Por cada publicación pendiente: crea el contenedor con la URL pública de la
imagen (`/v1/instagram/media/{id}.jpg`, que Instagram descarga), espera a que
esté FINISHED y la publica. Los fallos se reintentan en los siguientes pasos
(hasta 5 intentos y 24 h); después queda en error y se avisa al canal Admin.

Como en Telegram, si Instagram no responde al publicar, el post pudo salir:
se da por publicado y se avisa para revisarlo, en vez de arriesgar un duplicado.

Token: el de `INSTAGRAM_ACCESS_TOKEN` siembra `instagram_account`; se renueva
cada 7 días (dura 60) y la tabla guarda el vigente. Si se cambia en el .env, se
usa el nuevo. Un token inválido para la cola y avisa (como mucho cada 12 h).
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from app.core.config import Settings
from app.core.jobs import job_session
from app.modules.instagram.domain.models import POST_ERROR, POST_PUBLISHED, InstagramAccount, InstagramPost
from app.modules.instagram.infrastructure.graph_client import InstagramApiError, InstagramGraphClient
from app.modules.instagram.infrastructure.repository import InstagramRepository

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
MAX_AGE = timedelta(hours=24)
REFRESH_EVERY = timedelta(days=7)
ALERT_EVERY = timedelta(hours=12)


def media_url(settings: Settings, post_id: str) -> str:
    return f"{settings.public_api_url.rstrip('/')}/v1/instagram/media/{post_id}.jpg"


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class _TokenInvalid(Exception):
    pass


class InstagramPublisher:
    def __init__(
        self,
        session,
        repo: InstagramRepository,
        settings: Settings,
        *,
        client_factory: Callable[..., InstagramGraphClient] = InstagramGraphClient,
        notify: Callable[[str], object] | None = None,
    ):
        self.session = session
        self.repo = repo
        self.settings = settings
        self.client_factory = client_factory
        self.notify = notify

    async def run(self, now: datetime | None = None) -> int:
        """Publica lo pendiente; devuelve cuántas publicaciones salieron."""
        if not self.settings.instagram_enabled:
            return 0
        now = now or datetime.now(timezone.utc)
        account = await self._account(now)
        await self.session.commit()
        if account is None or not account.user_id:
            return 0

        client = self.client_factory(account.access_token, self.settings.instagram_graph_version)
        published = 0
        for post_id in await self.repo.pending_ids():
            try:
                post = await self.repo.lock_pending(post_id)
                if post is not None:
                    published += await self._publish_one(post, client, account.user_id, now)
                await self.session.commit()
            except _TokenInvalid as exc:
                await self.session.commit()  # guarda el intento antes de parar
                await self._token_problem(str(exc), now)
                break
            except Exception:
                logger.exception("Instagram: error de BD con la publicación %s", post_id)
                await self.session.rollback()
        return published

    # ── Cuenta y token ──────────────────────────────────────────────────────

    async def _account(self, now: datetime) -> InstagramAccount | None:
        env_token = (self.settings.instagram_access_token or "").strip()
        account = await self.repo.account(for_update=True)
        if env_token and (account is None or account.seed_hash != _hash(env_token)):
            account = account or InstagramAccount(id=1)
            account.access_token = env_token
            account.seed_hash = _hash(env_token)
            account.user_id = None
            account.username = None
            account.refreshed_at = now
            account.expires_at = None
            account.last_error = None
            await self.repo.save_account(account)
        if account is None:
            logger.info("Instagram activado pero sin INSTAGRAM_ACCESS_TOKEN; no se publica")
            return None

        client = self.client_factory(account.access_token, self.settings.instagram_graph_version)
        refreshing = False
        try:
            configured_id = (self.settings.instagram_user_id or "").strip()
            if not account.user_id or (configured_id and account.user_id != configured_id):
                if configured_id:
                    info = await asyncio.to_thread(client.account_info, configured_id)
                    account.user_id = configured_id
                else:
                    info = await asyncio.to_thread(client.me)
                    account.user_id = str(info.get("user_id") or info.get("id") or "") or None
                account.username = info.get("username")
                logger.info("Instagram conectado como @%s", account.username)
            elif client.refreshable and now - _aware(account.refreshed_at) >= REFRESH_EVERY:
                refreshing = True
                fresh = await asyncio.to_thread(client.refresh_token)
                account.access_token = fresh.access_token
                account.refreshed_at = now
                account.expires_at = now + timedelta(seconds=int(fresh.expires_in)) if fresh.expires_in else None
                logger.info("Instagram: token renovado")
            account.last_error = None
        except InstagramApiError as exc:
            account.last_error = str(exc)[:500]
            if exc.token_invalid or (not account.user_id and not exc.transient):
                await self._token_problem(str(exc), now, account)
                return None
            logger.warning("Instagram: fallo al comprobar la cuenta o renovar el token (%s); se reintenta", exc)
            if refreshing:
                # Reintento de la renovación en 6 h (el token sigue valiendo semanas).
                account.refreshed_at = now - REFRESH_EVERY + timedelta(hours=6)
        await self.repo.save_account(account)
        return account if account.user_id else None

    async def _token_problem(self, detail: str, now: datetime, account: InstagramAccount | None = None) -> None:
        account = account or await self.repo.account(for_update=True)
        logger.error("Instagram: token no válido o cuenta no accesible: %s", detail)
        if account is None:
            return
        account.last_error = detail[:500]
        if account.alerted_at is None or now - account.alerted_at >= ALERT_EVERY:
            account.alerted_at = now
            await self._notify(
                "⚠️ Instagram: no se puede publicar (token caducado, revocado o sin permisos). "
                f"Genera un token nuevo y ponlo en INSTAGRAM_ACCESS_TOKEN. Detalle: {detail[:200]}"
            )
        await self.repo.save_account(account)
        await self.session.commit()

    # ── Publicaciones ───────────────────────────────────────────────────────

    async def _publish_one(self, post: InstagramPost, client: InstagramGraphClient, user_id: str, now: datetime) -> int:
        if now - _aware(post.created_at) > MAX_AGE or post.attempts >= MAX_ATTEMPTS:
            await self._fail(post)
            return 0
        try:
            if not post.container_id:
                post.container_id = await asyncio.to_thread(
                    client.create_image_container, user_id, media_url(self.settings, post.id), post.caption
                )
            status = await asyncio.to_thread(client.container_status, post.container_id)
            if status == "IN_PROGRESS":
                return 0  # Instagram aún procesa la imagen: siguiente paso del job
            if status in {"ERROR", "EXPIRED"}:
                post.container_id = None
                post.attempts += 1
                post.last_error = f"Contenedor en estado {status}"
                return 0
            if status == "PUBLISHED":
                self._published(post, None, now)
                return 1
            self._published(post, await asyncio.to_thread(client.publish, user_id, post.container_id), now)
            return 1
        except InstagramApiError as exc:
            if exc.unknown:
                self._published(post, None, now)
                post.last_error = "Instagram no confirmó la publicación (tiempo agotado); se da por publicada"
                await self._notify(f"⚠️ Instagram no confirmó una publicación; revisa el feed. {post.caption[:80]}")
                return 1
            post.attempts += 1
            post.last_error = str(exc)[:500]
            if exc.token_invalid:
                raise _TokenInvalid(str(exc)) from None
            logger.warning("Instagram: intento %d fallido para %s: %s", post.attempts, post.id, exc)
            if post.attempts >= MAX_ATTEMPTS:
                await self._fail(post)
            return 0

    @staticmethod
    def _published(post: InstagramPost, media_id: str | None, now: datetime) -> None:
        post.status = POST_PUBLISHED
        post.media_id = media_id
        post.published_at = now
        post.image = None  # ya no hace falta servirla
        post.last_error = None

    async def _fail(self, post: InstagramPost) -> None:
        post.status = POST_ERROR
        title = post.caption.split("\n", 1)[0][:100]
        logger.error("Instagram: publicación %s descartada: %s", post.id, post.last_error)
        await self._notify(
            f"⚠️ No se pudo publicar en Instagram: {title}. {(post.last_error or 'caducada')[:200]}"
        )

    async def _notify(self, text: str) -> None:
        if self.notify is None:
            return
        try:
            await asyncio.to_thread(self.notify, text)
        except Exception:
            logger.warning("Instagram: no se pudo avisar al canal Admin", exc_info=True)


async def _run(settings: Settings) -> int:
    if not settings.instagram_enabled or not settings.database_url:
        return 0
    from app.modules.telegram.infrastructure.telegram_bot import TelegramBot

    def notify(text: str) -> None:
        if settings.telegram_bot_token and settings.telegram_admin_channel_id:
            TelegramBot(settings.telegram_bot_token).send_admin_notification(
                text, chat_id=settings.telegram_admin_channel_id
            )

    async with job_session(settings) as session:
        try:
            return await InstagramPublisher(session, InstagramRepository(session), settings, notify=notify).run()
        except Exception:
            await session.rollback()
            logger.exception("Fallo global del job de Instagram")
            return 0


def run_instagram_queue(settings: Settings) -> int:
    """Job síncrono para APScheduler. Con INSTAGRAM_ENABLED=false no hace nada."""
    return asyncio.run(_run(settings))
