import logging
from datetime import datetime, timezone
from app.modules.affiliates.domain.links import InvalidLinkError, canonicalize
from app.modules.deals.domain.exceptions import DuplicateDealError
from app.modules.deals.domain.models import Deal
from app.modules.deals.domain.utils import auto_slug
from app.modules.deals.infrastructure.repository import DealRepository
from app.modules.alerts.application.alert_matcher import AlertMatcher

logger = logging.getLogger(__name__)


# Datos propios de una oferta concreta: al reactivar un chollo con un alta nueva
# no se arrastran los de la oferta anterior (p. ej. un expires_at ya pasado lo
# volvería a caducar en minutos) salvo que el alta los traiga.
_OFFER_FIELDS = ("expires_at", "scheduled_for", "coupon_code", "previous_price", "discount_percentage", "savings_amount")


class DealService:
    def __init__(self, repo: DealRepository, matcher: AlertMatcher | None = None, catalog=None):
        """`matcher` es opcional: cuando se inyecta, los altas/actualizaciones de
        chollos activos disparan notificaciones de alertas coincidentes. Esto
        permite testar `DealService` aislado sin tocar el módulo de alerts.

        `catalog` (CatalogRepository) vincula cada chollo nuevo a su producto y
        tienda del catálogo permanente."""
        self.repo = repo
        self.matcher = matcher
        self.catalog = catalog

    async def _check_external_id_unique(
        self, external_id: str | None, *, exclude_id: str | None = None
    ) -> None:
        """Si `external_id` viene informado, comprueba que no exista en otro deal.

        Lanza `DuplicateDealError` con los datos del existente para que el
        frontend ofrezca al admin sobrescribir o saltar a editar.
        """
        if not external_id:
            return
        existing = await self.repo.find_by_external_id(
            external_id, exclude_id=exclude_id
        )
        if existing is not None:
            raise DuplicateDealError(
                existing_id=existing.id,
                existing_slug=existing.slug,
                existing_title=existing.title,
            )

    @staticmethod
    def _canonical_url_for(affiliate_url: str | None, external_id: str | None) -> str | None:
        if not affiliate_url:
            return None
        try:
            link = canonicalize(affiliate_url, asin=external_id)
        except InvalidLinkError:
            return None
        return link.canonical_url if link.host else None

    async def create_deal(self, deal_data: dict, user_id: str, revive_id: str | None = None) -> Deal:
        """Alta de un chollo. Catálogo permanente: si el producto ya tiene un
        chollo sin oferta (`expired`) se reactiva ese mismo (misma URL, votos y
        comentarios) en vez de crear otro. `revive_id` lo indica el llamante
        cuando ya lo encontró por otra vía (p. ej. por URL canónica)."""
        existing = await self.repo.get_by_id(revive_id) if revive_id else None
        if existing is None and deal_data.get("external_id"):
            existing = await self.repo.find_by_external_id(deal_data["external_id"], exclude_id=None)
            if existing is not None and existing.status != "expired":
                raise DuplicateDealError(
                    existing_id=existing.id,
                    existing_slug=existing.slug,
                    existing_title=existing.title,
                )

        if await self.repo.user_has_profile(user_id):
            deal_data["created_by"] = user_id
            logger.debug("created_by asignado a user_id=%s", user_id)
        else:
            deal_data.pop("created_by", None)
            logger.warning("Perfil no encontrado para user_id=%s; created_by quedará NULL", user_id)

        deal_data["canonical_url"] = self._canonical_url_for(
            deal_data.get("affiliate_url"), deal_data.get("external_id")
        )

        if existing is not None:
            deal = await self._revive(existing, deal_data)
        else:
            if not deal_data.get("slug"):
                deal_data["slug"] = auto_slug(deal_data["title"])
            created = await self.repo.create(Deal(**deal_data))
            if self.catalog is not None:
                await self.catalog.link_new_deal(created)
            deal = await self.repo.get_by_id(created.id)
        if self.matcher and deal.status == "active":
            await self.matcher.notify_matching_alerts(deal)
        return deal

    async def _revive(self, deal: Deal, deal_data: dict) -> Deal:
        """Reutiliza el chollo existente con los datos nuevos (sin tocar su slug,
        votos ni fecha de creación) y lo vuelve a poner en oferta."""
        for field in _OFFER_FIELDS:
            if field not in deal_data:
                setattr(deal, field, None)
        for field, value in deal_data.items():
            if field != "slug":
                setattr(deal, field, value)
        deal.status = deal_data.get("status") or "active"
        deal.offer_end_reason = None
        deal.offer_price = deal.current_price
        if deal.status == "active":
            deal.published_at = datetime.now(timezone.utc)
        await self.repo.update(deal)
        if self.catalog is not None and deal.listing_id is None:
            await self.catalog.link_new_deal(deal)
        logger.info("Chollo %s reactivado por un alta del mismo producto", deal.id)
        return await self.repo.reload(deal.id)

    async def update_deal(self, deal_id: str, update_data: dict) -> Deal | None:
        deal = await self.repo.get_by_id(deal_id)
        if not deal:
            return None
        # Sólo validamos si el campo external_id viene en el payload del PUT.
        # Si no viene, conservamos el valor actual y no hay nada que comprobar.
        if "external_id" in update_data:
            await self._check_external_id_unique(
                update_data["external_id"], exclude_id=deal_id
            )
        for field, value in update_data.items():
            setattr(deal, field, value)
        if "affiliate_url" in update_data or "external_id" in update_data:
            deal.canonical_url = self._canonical_url_for(deal.affiliate_url, deal.external_id)
        await self.repo.update(deal)
        updated = await self.repo.get_by_id(deal_id)
        # AlertMatcher comprueba internamente que status == "active".
        if updated and self.matcher:
            await self.matcher.notify_matching_alerts(updated)
        return updated

    async def delete_deal(self, deal_id: str) -> bool:
        deal = await self.repo.get_by_id(deal_id)
        if not deal:
            return False
        product_id = deal.product_id
        await self.repo.delete(deal)
        # Borrado manual del último chollo de un producto: no dejar la ficha y
        # sus tiendas huérfanas (la revisión diaria las seguiría consultando).
        if self.catalog is not None and product_id:
            await self.catalog.delete_product_if_orphan(product_id)
        return True

    async def process_vote(self, deal_id: str, user_id: str, vote: int) -> dict:
        """Aplica el voto (toggle si es el mismo) y devuelve los contadores actualizados."""
        current_vote = await self.repo.get_user_vote(deal_id, user_id)

        if current_vote == vote:
            await self.repo.delete_vote(deal_id, user_id)
            my_vote = 0
        else:
            await self.repo.upsert_vote(deal_id, user_id, vote)
            my_vote = vote

        counters = await self.repo.recalculate_votes(deal_id)
        return {**counters, "my_vote": my_vote}
