from __future__ import annotations

from sqlalchemy import and_, delete, insert, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.affiliates.domain.models import AffiliateFeedProduct, AffiliateProgram
from app.modules.affiliates.domain.offers import url_matches
from app.modules.deals.domain.models import Deal


def active_generations(program: AffiliateProgram) -> list[tuple[str, int]]:
    """(feed_id, generation) publicadas: solo las de sincronizaciones completas."""
    out = []
    for feed in program.feeds or []:
        gen = feed.get("generation")
        if feed.get("selected") and feed.get("available") is not False and feed.get("feed_id") and isinstance(gen, int):
            out.append((str(feed["feed_id"]), gen))
    return out


class AffiliateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Programas ───────────────────────────────────────────────────────────

    async def list_programs(self) -> list[AffiliateProgram]:
        result = await self.session.execute(select(AffiliateProgram).order_by(AffiliateProgram.name))
        return list(result.scalars().all())

    async def get_program(self, program_id: str) -> AffiliateProgram | None:
        return await self.session.get(AffiliateProgram, program_id)

    async def programs_for_url(self, url: str) -> list[AffiliateProgram]:
        return [p for p in await self.list_programs() if url_matches(url, p.domains or [])]

    async def save(self, program: AffiliateProgram) -> AffiliateProgram:
        self.session.add(program)
        await self.session.commit()
        await self.session.refresh(program)
        return program

    # ── Catálogo local de feeds ─────────────────────────────────────────────

    def _active_filter(self, program: AffiliateProgram):
        gens = active_generations(program)
        if not gens:
            return None
        return and_(
            AffiliateFeedProduct.program_id == program.id,
            tuple_(AffiliateFeedProduct.feed_id, AffiliateFeedProduct.generation).in_(gens),
        )

    async def find_feed_products(
        self,
        program: AffiliateProgram,
        *,
        normalized_url: str | None = None,
        ean: str | None = None,
        merchant_product_id: str | None = None,
        product_key: str | None = None,
        limit: int = 20,
    ) -> list[AffiliateFeedProduct]:
        base = self._active_filter(program)
        if base is None:
            return []
        conds = []
        if normalized_url:
            conds.append(AffiliateFeedProduct.normalized_url == normalized_url)
        if ean:
            conds.append(AffiliateFeedProduct.ean == ean)
        if merchant_product_id:
            conds.append(AffiliateFeedProduct.merchant_product_id == merchant_product_id)
        if product_key:
            conds.append(AffiliateFeedProduct.product_key == product_key)
        if not conds:
            return []
        result = await self.session.execute(select(AffiliateFeedProduct).where(base, or_(*conds)).limit(limit))
        return list(result.scalars().all())

    async def feed_candidates(self, program: AffiliateProgram, words: list[str], limit: int = 50) -> list[AffiliateFeedProduct]:
        """Filas cuyo título contiene alguna de las palabras (el caso de uso las ordena)."""
        base = self._active_filter(program)
        if base is None or not words:
            return []
        conds = [AffiliateFeedProduct.title.ilike(f"%{w.replace('%', '').replace('_', '')}%") for w in words[:6]]
        result = await self.session.execute(select(AffiliateFeedProduct).where(base, or_(*conds)).limit(limit))
        return list(result.scalars().all())

    async def insert_feed_rows(self, rows: list[dict]) -> None:
        if rows:
            await self.session.execute(insert(AffiliateFeedProduct), rows)

    async def delete_generation(self, program_id: str, feed_id: str, *, keep: int | None = None, only: int | None = None) -> None:
        stmt = delete(AffiliateFeedProduct).where(
            AffiliateFeedProduct.program_id == program_id, AffiliateFeedProduct.feed_id == feed_id
        )
        if keep is not None:
            stmt = stmt.where(AffiliateFeedProduct.generation != keep)
        if only is not None:
            stmt = stmt.where(AffiliateFeedProduct.generation == only)
        await self.session.execute(stmt)

    # ── Deals ya existentes ─────────────────────────────────────────────────

    async def deal_by_external_id(self, external_id: str) -> Deal | None:
        result = await self.session.execute(select(Deal).where(Deal.external_id == external_id).limit(1))
        return result.scalars().first()
