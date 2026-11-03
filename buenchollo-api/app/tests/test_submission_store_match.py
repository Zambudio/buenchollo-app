"""find_store_by_host: exact and subdomain-by-suffix matching."""

from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.asyncio

from app.modules.submissions.infrastructure.repository import SubmissionRepository

DOMAINS = ["aliexpress.com", "amazon.es", "mediamarkt.es", "mi.com", "pccomponentes.com", "pc.com"]


class FakeSession:
    async def execute(self, stmt):
        stores = [SimpleNamespace(name=d, domain=d) for d in DOMAINS]
        return SimpleNamespace(scalars=lambda: iter(stores))


@pytest.mark.parametrize(
    "host,expected",
    [
        ("aliexpress.com", "aliexpress.com"),
        ("www.aliexpress.com", "aliexpress.com"),
        ("es.aliexpress.com", "aliexpress.com"),
        ("m.mediamarkt.es", "mediamarkt.es"),
        ("tienda.mi.com", "mi.com"),
        ("xiaomi.com", None),
        ("www.xiaomi.com", None),
        ("notamazon.es", None),
        ("evilpccomponentes.com", None),
        ("", None),
    ],
)
async def test_find_store_by_host(host, expected):
    store = await SubmissionRepository(FakeSession()).find_store_by_host(host)
    assert (store.domain if store else None) == expected


async def test_longest_domain_wins():
    class Session:
        async def execute(self, stmt):
            stores = [SimpleNamespace(name="a", domain="com"), SimpleNamespace(name="b", domain="shop.example.com")]
            return SimpleNamespace(scalars=lambda: iter(stores))

    store = await SubmissionRepository(Session()).find_store_by_host("x.shop.example.com")
    assert store.name == "b"
