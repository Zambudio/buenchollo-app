"""Caso de uso: URL de producto → oferta lista para el editor (sin publicar).

Recorrido: validar URL → detectar tienda y programa → comprobar configuración
y adhesión → buscar el producto en una fuente autorizada (catálogo local de
feeds de Awin / Products API de Tradedoubler) → obtener el enlace afiliado
oficial → devolver la oferta común con procedencia, antigüedad, campos que
faltan y motivos que impiden publicar.

Nunca publica, nunca hace scraping de la tienda y nunca fabrica un enlace si la
red no lo devuelve (salvo el deeplink de Tradedoubler confirmado a mano por el
propietario para ese programa).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urlsplit

from app.modules.affiliates.domain.links import _is_public_store_netloc, extract_url, is_amazon_host, is_amazon_short_host
from app.modules.affiliates.domain.models import (
    MEMBERSHIP_JOINED,
    NETWORK_AWIN,
    NETWORK_TRADEDOUBLER,
    AffiliateFeedProduct,
    AffiliateProgram,
)
from app.modules.affiliates.domain.offers import (
    REF_NONE,
    REF_PROVIDER_HISTORY_30D,
    SOURCE_AWIN_FEED,
    SOURCE_LINK_ONLY,
    SOURCE_TRADEDOUBLER_API,
    ImportedOffer,
    OfferData,
    ProductData,
    ProviderRef,
    data_freshness,
    describe_blockers,
    destination_url,
    lowest_price_last_30_days,
    is_network_tracking_url,
    missing_fields,
    normalize_product_url,
    parse_money,
    short_summary,
    slug_keywords,
)
from app.modules.affiliates.infrastructure.awin_client import AwinClient, AwinLinkUnavailable
from app.modules.affiliates.infrastructure.http import NetworkAuthError, NetworkError, NetworkRateLimited, redact
from app.modules.affiliates.infrastructure.repository import AffiliateRepository, active_generations
from app.modules.affiliates.infrastructure.tradedoubler_client import TD_TRACKING_HOSTS, TradedoublerClient, map_td_product

logger = logging.getLogger(__name__)

# Estados que entiende el editor (Fase E).
ST_UNSUPPORTED = "unsupported_store"
ST_USE_AMAZON = "use_amazon_flow"
ST_CHOOSE_PROGRAM = "program_choice_required"
ST_DISABLED = "program_disabled"
ST_NOT_CONFIGURED = "not_configured"
ST_PENDING = "pending_approval"
ST_CATALOG_UNAVAILABLE = "catalog_unavailable"
ST_NO_MATCH = "no_match"
ST_AMBIGUOUS = "ambiguous"
ST_RATE_LIMITED = "rate_limited"
ST_PROVIDER_ERROR = "provider_error"
ST_LINK_ONLY = "link_only"
ST_IMPORTED = "imported"
ST_STALE = "stale_data"

MAX_TD_FEEDS_PER_IMPORT = 3


@dataclass
class ImportRequest:
    url: str
    program_id: str | None = None
    product_key: str | None = None
    ean: str | None = None
    sku: str | None = None
    link_only: bool = False


@dataclass
class ImportResult:
    status: str
    message: str
    stage: str = "none"  # none | link_generated | product_imported
    program: dict | None = None
    program_options: list[dict] = field(default_factory=list)
    link: dict = field(default_factory=lambda: {"status": "not_requested"})
    offer: dict | None = None
    provenance: dict | None = None
    missing: list[str] = field(default_factory=list)
    blockers: list[dict] = field(default_factory=list)
    candidates: list[dict] = field(default_factory=list)
    existing_deal: dict | None = None
    warnings: list[str] = field(default_factory=list)


def program_summary(p: AffiliateProgram) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "network": p.network,
        "advertiser_id": p.advertiser_id,
        "membership_status": p.membership_status,
        "membership_checked_at": p.membership_checked_at.isoformat() if p.membership_checked_at else None,
        "enabled": p.enabled,
        "disclosure_text": p.disclosure_text,
        "image_channels": list((p.restrictions or {}).get("image_channels") or []),
        "max_data_age_hours": p.max_data_age_hours,
        "store_id": p.store_id,
    }


def _shipping_text(raw: str | None) -> str | None:
    if not raw:
        return None
    amount = parse_money(raw)
    if amount is None:
        return f"Envío: {raw.strip()[:60]} (según la red)"
    euros = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"Envío: {euros} € (según la red)"


def _public_image(url: str | None) -> str | None:
    if not url:
        return None
    parts = urlsplit(url)
    return url if parts.scheme == "https" and _is_public_store_netloc(parts.netloc) else None


def _dec(value) -> Decimal | None:
    return parse_money(value) if value is not None else None


def _money_out(value: Decimal | None) -> str | None:
    return f"{value:.2f}" if value is not None else None


class ImportOfferUseCase:
    def __init__(self, repo: AffiliateRepository, awin: AwinClient, tradedoubler: TradedoublerClient) -> None:
        self.repo = repo
        self.awin = awin
        self.td = tradedoubler

    async def execute(self, req: ImportRequest, now: datetime | None = None) -> ImportResult:
        now = now or datetime.now(timezone.utc)
        url = extract_url(req.url)  # valida http(s), host público, sin credenciales ni IPs
        host = (urlsplit(url).hostname or "").lower()
        if is_amazon_host(host) or is_amazon_short_host(host):
            return ImportResult(ST_USE_AMAZON, "Es un enlace de Amazon: se usa el autorrelleno de Amazon.")

        programs = await self.repo.programs_for_url(url)
        if not programs:
            return ImportResult(ST_UNSUPPORTED, "Ninguna tienda configurada (Awin/Tradedoubler) coincide con este dominio.")
        if req.program_id:
            programs = [p for p in programs if p.id == req.program_id]
            if not programs:
                return ImportResult(ST_UNSUPPORTED, "El programa elegido no corresponde a este dominio.")
        if len(programs) > 1:
            return ImportResult(
                ST_CHOOSE_PROGRAM,
                "Hay varios programas para esta tienda: elige cuál corresponde (no se elige automáticamente).",
                program_options=[program_summary(p) for p in programs],
            )
        program = programs[0]
        summary = program_summary(program)
        dest = destination_url(url)

        if not program.enabled:
            return ImportResult(ST_DISABLED, "El programa está deshabilitado en el registro de tiendas.", program=summary)
        if program.network == NETWORK_AWIN and not self.awin.api_configured:
            return ImportResult(ST_NOT_CONFIGURED, "Faltan AWIN_PUBLISHER_ID / AWIN_ACCESS_TOKEN en el servidor.", program=summary)
        if program.network == NETWORK_TRADEDOUBLER and not self.td.configured:
            return ImportResult(ST_NOT_CONFIGURED, "Falta TRADEDOUBLER_PRODUCTS_TOKEN en el servidor.", program=summary)
        if program.membership_status != MEMBERSHIP_JOINED:
            return ImportResult(
                ST_PENDING,
                f"Programa no aprobado (estado: {program.membership_status}). No se generan enlaces ni se importa.",
                program=summary,
            )

        try:
            if program.network == NETWORK_AWIN:
                return await self._awin(program, summary, req, url, dest, now)
            return await self._tradedoubler(program, summary, req, url, dest, now)
        except NetworkRateLimited as exc:
            return ImportResult(ST_RATE_LIMITED, str(exc), program=summary)
        except (NetworkAuthError, NetworkError) as exc:
            secrets = self.awin.secrets + self.td.secrets
            return ImportResult(ST_PROVIDER_ERROR, redact(str(exc), secrets), program=summary)

    # ── Awin ────────────────────────────────────────────────────────────────

    async def _awin(self, program, summary, req: ImportRequest, url: str, dest: str, now) -> ImportResult:
        warnings: list[str] = []
        row: AffiliateFeedProduct | None = None
        candidates: list[AffiliateFeedProduct] = []
        status = None

        if not req.link_only:
            if not program.supports_import or not active_generations(program):
                status = ST_CATALOG_UNAVAILABLE
            else:
                matches = await self.repo.find_feed_products(
                    program,
                    normalized_url=None if (req.product_key or req.ean or req.sku) else normalize_product_url(url),
                    product_key=req.product_key,
                    ean=req.ean,
                    merchant_product_id=req.sku,
                )
                matches = _dedupe_rows(matches)
                if len(matches) == 1:
                    row = matches[0]
                elif len(matches) > 1:
                    status, candidates = ST_AMBIGUOUS, matches
                else:
                    status = ST_NO_MATCH
                    words = slug_keywords(url)
                    candidates = rank_candidates(await self.repo.feed_candidates(program, words), words, lambda r: r.title)

        link_dest = row.merchant_url if row and row.merchant_url else dest
        link = await self._awin_link(program, link_dest, row, warnings)

        if row is None:
            result = ImportResult(
                status or ST_LINK_ONLY,
                _no_product_message(status, link),
                stage="link_generated" if link.get("affiliate_url") else "none",
                program=summary,
                link=link,
                candidates=[_awin_candidate(c) for c in candidates],
                warnings=warnings,
            )
            if link.get("affiliate_url"):
                result.offer = self._link_only_offer(program, url, dest, link)
                result.provenance = {"data_source": SOURCE_LINK_ONLY, "imported_at": now.isoformat()}
                result.missing = ["title", "current_price", "previous_price_evidence", "shipping_info", "image_url", "description", "category"]
            return result

        offer = ImportedOffer(
            provider=ProviderRef(NETWORK_AWIN, program.id, program.advertiser_id, program.name, row.feed_id),
            store_name=program.name,
            store_id=program.store_id,
            original_url=url,
            destination_url=link_dest,
            affiliate_url=link.get("affiliate_url"),
            link_source=link.get("source"),
            product=ProductData(
                product_key=row.product_key,
                merchant_product_id=row.merchant_product_id,
                title=row.title,
                brand=row.brand,
                model=row.model,
                description=row.description,
                specs=dict(row.specs or {}),
                ean=row.ean,
                mpn=row.mpn,
                colour=row.colour,
                condition=row.condition,
                image_url=_public_image(row.image_url),
                category_hint=row.category,
            ),
            offer=OfferData(
                current_price=_dec(row.price),
                currency=row.currency or program.currency,
                rrp_price=_dec(row.rrp_price),
                reference_type=REF_NONE,
                shipping=_shipping_text(row.delivery_cost),
                in_stock=row.in_stock,
            ),
            data_source=SOURCE_AWIN_FEED,
            provider_updated_at=row.provider_updated_at,
            imported_at=row.imported_at or now,
        )
        if offer.offer.rrp_price is not None:
            warnings.append("El feed trae PVP recomendado: se muestra aparte y no cuenta como precio anterior.")
        return await self._finish(program, summary, offer, link, now, warnings)

    async def _awin_link(self, program, dest: str, row, warnings: list[str]) -> dict:
        if not program.supports_links:
            return {"status": "unavailable", "message": "El programa no admite generación de enlaces en el registro."}
        try:
            url = await asyncio.to_thread(self.awin.generate_link, program.advertiser_id, dest, "bct-editor")
            return {"status": "generated", "affiliate_url": url, "source": "awin_linkbuilder"}
        except AwinLinkUnavailable as exc:
            # El aw_deep_link del feed también lo genera Awin para nuestra cuenta:
            # es un enlace oficial, no uno construido por nosotros.
            if row is not None and row.tracking_url:
                warnings.append("Link Builder no devolvió enlace; se usa el aw_deep_link oficial del feed.")
                return {"status": "generated", "affiliate_url": row.tracking_url, "source": "awin_feed_deeplink"}
            return {"status": "error", "message": str(exc)}

    # ── Tradedoubler ────────────────────────────────────────────────────────

    async def _tradedoubler(self, program, summary, req: ImportRequest, url: str, dest: str, now) -> ImportResult:
        warnings: list[str] = []
        feeds = [str(f["feed_id"]) for f in (program.feeds or []) if f.get("selected") and f.get("feed_id")]
        product = None
        candidates: list[dict] = []
        status = None

        if not req.link_only:
            if not program.supports_import or not feeds:
                status = ST_CATALOG_UNAVAILABLE
            else:
                target = normalize_product_url(url)
                found: dict[str, dict] = {}
                query = None if (req.ean or req.sku) else " ".join(slug_keywords(url)) or None
                for feed_id in feeds[:MAX_TD_FEEDS_PER_IMPORT]:
                    items = await asyncio.to_thread(
                        self.td.search_products, feed_id, ean=req.ean, sp_id=req.sku, query=query, page_size=20
                    )
                    for item in items:
                        mapped = map_td_product(item, feed_id)
                        if mapped and mapped.get("product_key"):
                            mapped["feed_id"] = feed_id
                            found.setdefault(mapped["product_key"], mapped)
                pool = list(found.values())
                if req.product_key:
                    exact = [m for m in pool if m["product_key"] == req.product_key]
                elif req.ean or req.sku:
                    exact = pool
                else:
                    exact = [m for m in pool if normalize_product_url(m.get("merchant_url")) == target]
                if len(exact) == 1:
                    product = exact[0]
                elif len(exact) > 1:
                    status, candidates = ST_AMBIGUOUS, exact
                else:
                    status = ST_NO_MATCH
                    candidates = rank_candidates(pool, slug_keywords(url), lambda m: m.get("title") or "")

        link = self._td_link(program, product, dest)
        if product is None:
            result = ImportResult(
                status or ST_LINK_ONLY,
                _no_product_message(status, link),
                stage="link_generated" if link.get("affiliate_url") else "none",
                program=summary,
                link=link,
                candidates=[_td_candidate(c) for c in candidates],
                warnings=warnings,
            )
            if link.get("affiliate_url"):
                result.offer = self._link_only_offer(program, url, dest, link)
                result.provenance = {"data_source": SOURCE_LINK_ONLY, "imported_at": now.isoformat()}
                result.missing = ["title", "current_price", "previous_price_evidence", "shipping_info", "image_url", "description", "category"]
            return result

        current = product.get("price")
        reference = lowest_price_last_30_days(product.get("price_history") or [], current, now) if current else None
        shipping = product.get("shipping")
        offer = ImportedOffer(
            provider=ProviderRef(NETWORK_TRADEDOUBLER, program.id, program.advertiser_id, program.name, product["feed_id"]),
            store_name=program.name,
            store_id=program.store_id,
            original_url=url,
            destination_url=product.get("merchant_url") or dest,
            affiliate_url=link.get("affiliate_url"),
            link_source=link.get("source"),
            product=ProductData(
                product_key=product["product_key"],
                merchant_product_id=product.get("merchant_product_id"),
                title=product.get("title"),
                brand=product.get("brand"),
                model=product.get("model"),
                description=product.get("description"),
                specs=product.get("specs") or {},
                ean=product.get("ean"),
                mpn=product.get("mpn"),
                condition=product.get("condition"),
                image_url=_public_image(product.get("image_url")),
            ),
            offer=OfferData(
                current_price=current,
                currency=product.get("currency") or program.currency,
                reference_price=reference,
                reference_type=REF_PROVIDER_HISTORY_30D if reference else REF_NONE,
                reference_evidence=(
                    f"Precio mínimo de los 30 días anteriores a la bajada según el historial de precios "
                    f"de Tradedoubler (feed {product['feed_id']}): {reference:.2f} €"
                    if reference
                    else None
                ),
                shipping=_shipping_text(shipping),
                in_stock=product.get("in_stock"),
            ),
            data_source=SOURCE_TRADEDOUBLER_API,
            provider_updated_at=product.get("provider_updated_at"),
            imported_at=now,
        )
        return await self._finish(program, summary, offer, link, now, warnings)

    def _td_link(self, program, product, dest: str) -> dict:
        if not program.supports_links:
            return {"status": "unavailable", "message": "El programa no admite generación de enlaces en el registro."}
        if product and product.get("tracking_url"):
            host = (urlsplit(product["tracking_url"]).hostname or "").lower()
            if host in TD_TRACKING_HOSTS and is_network_tracking_url(product["tracking_url"]):
                return {"status": "generated", "affiliate_url": product["tracking_url"], "source": "tradedoubler_product"}
        if program.deeplink_verified_at is not None:
            try:
                url = self.td.deeplink(program.advertiser_id, (product or {}).get("merchant_url") or dest)
            except NetworkError as exc:
                return {"status": "error", "message": str(exc)}
            return {"status": "generated", "affiliate_url": url, "source": "tradedoubler_deeplink"}
        return {
            "status": "unavailable",
            "message": "Sin ficha en la API no hay enlace oficial: el deeplink de este programa no está verificado "
            "por el propietario (ver guía). No se fabrica un enlace.",
        }

    # ── Común ───────────────────────────────────────────────────────────────

    def _link_only_offer(self, program, url: str, dest: str, link: dict) -> dict:
        return {
            "store_id": program.store_id,
            "store_name": program.name,
            "original_url": url,
            "destination_url": dest,
            "affiliate_url": link.get("affiliate_url"),
            "link_source": link.get("source"),
            "affiliate_program_id": program.id,
            "data_source": SOURCE_LINK_ONLY,
        }

    async def _finish(self, program, summary, offer: ImportedOffer, link, now, warnings) -> ImportResult:
        freshness = data_freshness(offer.provider_updated_at, None, program.max_data_age_hours, now)
        status = ST_STALE if freshness == "stale" else ST_IMPORTED
        existing = await self.repo.deal_by_external_id(offer.external_id) if offer.external_id else None
        p, o = offer.product, offer.offer
        flat = {
            "title": p.title,
            "brand": p.brand,
            "model": p.model,
            "description": p.description,
            "short_description": short_summary(p.description),
            "specs": p.specs,
            "ean": p.ean,
            "mpn": p.mpn,
            "sku": p.merchant_product_id,
            "product_key": p.product_key,
            "colour": p.colour,
            "condition": p.condition,
            "seller": p.seller,
            "image_url": p.image_url,
            "category_hint": p.category_hint,
            "current_price": _money_out(o.current_price),
            "currency": o.currency,
            "tax_note": o.tax_note,
            "reference_price": _money_out(o.reference_price),
            "reference_type": o.reference_type,
            "reference_evidence": o.reference_evidence,
            "rrp_price": _money_out(o.rrp_price),
            "shipping_info": o.shipping,
            "in_stock": o.in_stock,
            "store_id": offer.store_id,
            "store_name": offer.store_name,
            "external_id": offer.external_id,
            "original_url": offer.original_url,
            "destination_url": offer.destination_url,
            "affiliate_url": offer.affiliate_url,
            "link_source": offer.link_source,
            "affiliate_program_id": program.id,
            "data_source": offer.data_source,
        }
        if o.currency and o.currency != "EUR":
            warnings.append(f"La moneda de la fuente es {o.currency}, no EUR.")
        message = "Producto importado: revisa los campos pendientes antes de guardar."
        if status == ST_STALE:
            message = "Producto importado con datos caducados: comprueba precio y envío en la tienda."
        if not offer.affiliate_url:
            message += " No se ha obtenido el enlace afiliado."
        return ImportResult(
            status=status,
            message=message,
            stage="product_imported",
            program=summary,
            link=link,
            offer=flat,
            provenance={
                "data_source": offer.data_source,
                "feed_id": offer.provider.feed_id,
                "provider_updated_at": offer.provider_updated_at.isoformat() if offer.provider_updated_at else None,
                "imported_at": offer.imported_at.isoformat(),
                "freshness": freshness,
                "max_data_age_hours": program.max_data_age_hours,
            },
            missing=missing_fields(offer),
            existing_deal=(
                {"id": existing.id, "slug": existing.slug, "title": existing.title, "status": existing.status}
                if existing
                else None
            ),
            warnings=warnings,
        )


def _no_product_message(status: str | None, link: dict) -> str:
    base = {
        ST_CATALOG_UNAVAILABLE: "Catálogo no disponible para este programa (sin feeds seleccionados o sin sincronizar).",
        ST_NO_MATCH: "Sin coincidencia exacta en el catálogo. Elige un candidato o indica EAN/SKU.",
        ST_AMBIGUOUS: "Varias variantes coinciden: elige la correcta (no se selecciona automáticamente).",
        None: "Solo se ha pedido el enlace.",
    }.get(status, "Sin ficha de producto.")
    if link.get("affiliate_url"):
        return base + " Enlace generado."
    if link.get("message"):
        return base + " " + link["message"]
    return base


def rank_candidates(items: list, words: list[str], title_of, limit: int = 8) -> list:
    """Candidatos por título: al menos la mitad de las palabras del slug, los
    que más coinciden primero. Solo se proponen; nunca se eligen solos."""
    if not words:
        return items[:limit]
    lowered = [w.lower() for w in words]
    needed = max(1, (len(lowered) + 1) // 2)
    scored = []
    for item in items:
        title = (title_of(item) or "").lower()
        score = sum(1 for w in lowered if w in title)
        if score >= needed:
            scored.append((score, item))
    scored.sort(key=lambda pair: -pair[0])
    return [item for _, item in scored[:limit]]


def _dedupe_rows(rows: list[AffiliateFeedProduct]) -> list[AffiliateFeedProduct]:
    best: dict[str, AffiliateFeedProduct] = {}
    for row in rows:
        current = best.get(row.product_key)
        if current is None or (row.provider_updated_at or datetime.min.replace(tzinfo=timezone.utc)) > (
            current.provider_updated_at or datetime.min.replace(tzinfo=timezone.utc)
        ):
            best[row.product_key] = row
    return list(best.values())


def _awin_candidate(row: AffiliateFeedProduct) -> dict:
    return {
        "product_key": row.product_key,
        "title": row.title,
        "price": _money_out(_dec(row.price)),
        "colour": row.colour,
        "condition": row.condition,
        "ean": row.ean,
        "sku": row.merchant_product_id,
        "url": row.merchant_url,
        "image_url": _public_image(row.image_url),
    }


def _td_candidate(m: dict) -> dict:
    return {
        "product_key": m.get("product_key"),
        "title": m.get("title"),
        "price": _money_out(m.get("price")),
        "colour": (m.get("specs") or {}).get("colour"),
        "condition": m.get("condition"),
        "ean": m.get("ean"),
        "sku": m.get("merchant_product_id"),
        "url": m.get("merchant_url"),
        "image_url": _public_image(m.get("image_url")),
    }


def result_to_dict(result: ImportResult) -> dict:
    return asdict(result)
