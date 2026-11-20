from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import delete, exists, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.catalog.domain.models import (
    AVAILABLE,
    SOURCE_AMAZON,
    SOURCE_MANUAL,
    PriceHistory,
    Product,
    ProductListing,
)
from app.modules.catalog.domain.price_history import SOURCE_DEAL, PricePoint, observed_day
from app.modules.deals.domain.models import Deal
from app.modules.stores.domain.models import Store

# Estados en los que un deal representa la oferta pública de su listing.
_PRIMARY_STATUSES = ("active", "expired")


class CatalogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_checkable(self) -> list[tuple[ProductListing, Deal | None]]:
        """Listings que la revisión diaria puede consultar (Amazon con ASIN), cada
        uno con su deal principal: el publicado más recientemente entre los
        `active`/`expired` (None si solo tiene borradores o programados)."""
        listings = list(
            (
                await self.session.execute(
                    select(ProductListing)
                    .where(
                        ProductListing.source == SOURCE_AMAZON,
                        ProductListing.external_id.is_not(None),
                        # Productos sin ningún chollo (huérfanos) no se consultan.
                        exists().where(Deal.product_id == ProductListing.product_id),
                    )
                    .order_by(ProductListing.id)
                )
            ).scalars()
        )
        if not listings:
            return []
        deals = (
            await self.session.execute(
                select(Deal)
                .options(selectinload(Deal.category), selectinload(Deal.subcategory), selectinload(Deal.store))
                .where(Deal.listing_id.in_([listing.id for listing in listings]), Deal.status.in_(_PRIMARY_STATUSES))
                .order_by(Deal.published_at.desc(), Deal.id)
            )
        ).scalars()
        primary: dict[str, Deal] = {}
        for deal in deals:
            primary.setdefault(deal.listing_id, deal)
        return [(listing, primary.get(listing.id)) for listing in listings]

    async def link_new_deal(self, deal: Deal) -> None:
        """Vincula un deal recién creado a su producto/listing (reutiliza el listing
        si ya existe la misma tienda + ASIN) y fija su `offer_price`."""
        external_id = (deal.external_id or "").strip().upper() or None
        listing = None
        if external_id:
            listing = (
                await self.session.execute(
                    select(ProductListing).where(
                        func.upper(ProductListing.external_id) == external_id,
                        ProductListing.store_id.is_(None)
                        if deal.store_id is None
                        else ProductListing.store_id == deal.store_id,
                    )
                )
            ).scalars().first()
        if listing is None:
            product = Product(
                slug=await self._free_slug(deal.slug),
                title=deal.title,
                brand=deal.brand,
                description=deal.description,
                short_description=deal.short_description,
                image_url=deal.image_url,
                images=list(deal.images or []),
                category_id=deal.category_id,
                subcategory_id=deal.subcategory_id,
            )
            self.session.add(product)
            await self.session.flush()
            listing = ProductListing(
                product_id=product.id,
                store_id=deal.store_id,
                source=await self._source_for(deal),
                external_id=external_id,
                canonical_url=deal.canonical_url,
                affiliate_url=deal.affiliate_url,
                current_price=deal.current_price,
                reference_price=deal.previous_price,
                discount_percentage=deal.discount_percentage,
            )
            self.session.add(listing)
            await self.session.flush()
        deal.product_id = listing.product_id
        deal.listing_id = listing.id
        deal.offer_price = deal.current_price
        await self.session.flush()
        await self.record_deal_price(deal)

    async def record_deal_price(self, deal: Deal, now: datetime | None = None) -> None:
        """Apunta en el histórico el precio con el que se publica o edita un
        chollo (sirve para cualquier tienda, no solo las que revisa el job)."""
        if deal.listing_id is None or deal.product_id is None:
            return
        await self.record_price(
            listing_id=deal.listing_id,
            product_id=deal.product_id,
            store_id=deal.store_id,
            price=deal.current_price,
            reference_price=deal.previous_price,
            in_stock=None,
            source=SOURCE_DEAL,
            now=now or datetime.now(timezone.utc),
        )

    async def record_price(
        self,
        *,
        listing_id: str,
        product_id: str,
        store_id: str | None,
        price,
        reference_price,
        in_stock: bool | None,
        source: str,
        now: datetime,
    ) -> None:
        """Un punto por listing y día: si ya hay uno ese día se actualiza con la
        última observación y se conserva el precio más bajo del día."""
        if price is None or Decimal(str(price)) <= 0:
            return
        values = dict(
            listing_id=listing_id,
            product_id=product_id,
            store_id=store_id,
            observed_on=observed_day(now),
            price=price,
            low_price=price,
            reference_price=reference_price,
            in_stock=in_stock,
            source=source,
            observed_at=now,
        )
        stmt = pg_insert(PriceHistory).values(**values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_price_history_listing_day",
            set_={
                "price": stmt.excluded.price,
                "low_price": func.least(PriceHistory.low_price, stmt.excluded.low_price),
                "reference_price": func.coalesce(stmt.excluded.reference_price, PriceHistory.reference_price),
                "in_stock": func.coalesce(stmt.excluded.in_stock, PriceHistory.in_stock),
                "source": stmt.excluded.source,
                "observed_at": stmt.excluded.observed_at,
            },
        )
        await self.session.execute(stmt)

    async def price_points(self, product_id: str, since: date | None = None) -> list[PricePoint]:
        """Puntos del histórico de un producto (todas sus tiendas), del más antiguo al más reciente."""
        query = select(
            PriceHistory.observed_on, PriceHistory.price, PriceHistory.low_price, PriceHistory.store_id
        ).where(PriceHistory.product_id == product_id)
        if since is not None:
            query = query.where(PriceHistory.observed_on >= since)
        rows = await self.session.execute(query.order_by(PriceHistory.observed_on, PriceHistory.store_id))
        return [
            PricePoint(observed_on=r.observed_on, price=Decimal(r.price), low_price=Decimal(r.low_price), store_id=r.store_id)
            for r in rows
        ]

    async def purge_listing(self, listing: ProductListing) -> list[str]:
        """Quita la tienda del producto. Si el producto se queda sin tiendas se
        eliminan el producto y sus deals; devuelve los ids de deals borrados."""
        others = list(
            (
                await self.session.execute(
                    select(ProductListing)
                    .where(ProductListing.product_id == listing.product_id, ProductListing.id != listing.id)
                    .order_by(
                        (ProductListing.availability != AVAILABLE),
                        ProductListing.current_price.asc().nulls_last(),
                        ProductListing.id,
                    )
                )
            ).scalars()
        )
        product_id, listing_id = listing.product_id, listing.id
        deleted: list[str] = []
        if others:
            await self.session.execute(
                update(Deal).where(Deal.listing_id == listing_id).values(listing_id=others[0].id)
            )
        else:
            deleted = list(
                (
                    await self.session.execute(
                        delete(Deal).where(Deal.product_id == product_id).returning(Deal.id)
                    )
                ).scalars()
            )
        await self.session.execute(delete(ProductListing).where(ProductListing.id == listing_id))
        if not others:
            await self.session.execute(delete(Product).where(Product.id == product_id))
        await self.session.flush()
        return deleted

    async def delete_orphan_products(self) -> int:
        """Elimina productos (y sus listings) sin ningún chollo: quedan así si un
        chollo se borra fuera de DealService (SQL directo, cascadas)."""
        result = await self.session.execute(
            delete(Product)
            .where(~exists().where(Deal.product_id == Product.id))
            .returning(Product.id)
            .execution_options(synchronize_session=False)
        )
        removed = len(result.all())
        await self.session.flush()
        return removed

    async def delete_product_if_orphan(self, product_id: str) -> bool:
        """Elimina el producto (y sus listings, en cascada) si ya no le queda
        ningún deal. Devuelve si lo eliminó."""
        if (await self.session.execute(select(Deal.id).where(Deal.product_id == product_id).limit(1))).first():
            return False
        await self.session.execute(delete(Product).where(Product.id == product_id))
        await self.session.flush()
        return True

    async def _free_slug(self, slug: str) -> str:
        taken = (await self.session.execute(select(Product.id).where(Product.slug == slug))).first()
        if taken is None:
            return slug
        suffix = 2
        while (await self.session.execute(select(Product.id).where(Product.slug == f"{slug}-{suffix}"))).first():
            suffix += 1
        return f"{slug}-{suffix}"

    async def _source_for(self, deal: Deal) -> str:
        urls = f"{deal.canonical_url or ''} {deal.affiliate_url or ''}".lower()
        if "amazon." in urls:
            return SOURCE_AMAZON
        if deal.store_id:
            name = (
                await self.session.execute(select(Store.name).where(Store.id == deal.store_id))
            ).scalar()
            if name and name.lower().startswith("amazon"):
                return SOURCE_AMAZON
        return SOURCE_MANUAL
