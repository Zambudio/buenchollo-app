import pytest

from app.core.exceptions import ValidationError
from app.modules.affiliates.domain.links import (
    InvalidLinkError,
    canonicalize,
    extract_url,
    is_amazon_host,
    is_amazon_short_host,
)
from app.modules.affiliates.domain.rewriters import (
    AMAZON_FOREIGN_MARKETPLACE,
    NOT_AFFILIABLE,
    THIRD_PARTY_AFFILIATE_REMOVED,
    rewrite_affiliate_link,
)

TAG = "buenchollo0b-21"


def test_extract_url_from_text_strips_trailing_punctuation():
    assert (
        extract_url("mira esto https://www.amazon.es/dp/B0ABCDEFGH?tag=otro-21 !!")
        == "https://www.amazon.es/dp/B0ABCDEFGH?tag=otro-21"
    )


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("www.pccomponentes.com/x", "https://www.pccomponentes.com/x"),
        ("amzn.to/3abc", "https://amzn.to/3abc"),
        ("(https://tienda.com/p).", "https://tienda.com/p"),
        ('"https://tienda.com/p",', "https://tienda.com/p"),
        ("http://tienda.com/p]", "http://tienda.com/p"),
    ],
)
def test_extract_url_variants(raw, expected):
    assert extract_url(raw) == expected


@pytest.mark.parametrize(
    "raw", ["hola", "javascript:alert(1)", "", "ftp://x.com/a", "https://" + "a" * 2050 + ".com"]
)
def test_extract_url_invalid(raw):
    with pytest.raises(InvalidLinkError):
        extract_url(raw)


def test_invalid_link_error_is_validation_error():
    assert issubclass(InvalidLinkError, ValidationError)


def test_canonicalize_amazon_dp_with_slug_and_tracking():
    link = canonicalize(
        "https://www.amazon.es/Some-Name/dp/B0ABCDEFGH/ref=sr_1_1?tag=otro-21&th=1"
    )
    assert link.canonical_url == "https://www.amazon.es/dp/B0ABCDEFGH"
    assert link.asin == "B0ABCDEFGH"
    assert link.host == "amazon.es"


def test_canonicalize_amazon_gp_aw_d():
    link = canonicalize("https://www.amazon.es/gp/aw/d/B0ABCDEFGH?psc=1")
    assert link.canonical_url == "https://www.amazon.es/dp/B0ABCDEFGH"
    assert link.asin == "B0ABCDEFGH"


def test_canonicalize_amazon_co_uk_and_explicit_asin():
    link = canonicalize("https://amazon.co.uk/whatever", asin="B0ABCDEFGH")
    assert link.canonical_url == "https://www.amazon.co.uk/dp/B0ABCDEFGH"


def test_canonicalize_generic():
    link = canonicalize("https://WWW.PcComponentes.com/item?utm_source=x&b=2&a=1#top")
    assert link.canonical_url == "https://pccomponentes.com/item?a=1&b=2"
    assert link.host == "pccomponentes.com"
    assert link.asin is None


def test_canonicalize_strips_trailing_slash_and_affiliate_params():
    link = canonicalize("https://tienda.com/p/?aff_id=1&affiliate_code=2&clickref=3&x=1")
    assert link.canonical_url == "https://tienda.com/p?x=1"


def test_host_helpers():
    assert is_amazon_host("amazon.es")
    assert is_amazon_host("www.amazon.co.uk")
    assert is_amazon_host("amazon.com.mx")
    assert is_amazon_host("amazon.co.jp")
    assert not is_amazon_host("amzn.to")
    assert not is_amazon_host("notamazon.es")
    assert not is_amazon_host("amazon.es.evil.com")
    for h in ("amzn.to", "amzn.eu", "a.co", "link.amazon"):
        assert is_amazon_short_host(h)
    assert not is_amazon_short_host("amazon.es")


def test_rewrite_amazon_es_replaces_foreign_tag():
    res = rewrite_affiliate_link(
        canonicalize("https://www.amazon.es/dp/B0ABCDEFGH?tag=otro-21"), amazon_tag=TAG
    )
    assert res.url == f"https://www.amazon.es/dp/B0ABCDEFGH?tag={TAG}"
    assert res.warnings == ()


def test_rewrite_amazon_foreign_marketplace():
    res = rewrite_affiliate_link(
        canonicalize("https://www.amazon.de/dp/B0ABCDEFGH?tag=otro-21"), amazon_tag=TAG
    )
    assert res.url == "https://www.amazon.de/dp/B0ABCDEFGH"
    assert AMAZON_FOREIGN_MARKETPLACE in res.warnings


def test_rewrite_amazon_without_asin():
    res = rewrite_affiliate_link(
        canonicalize("https://www.amazon.es/gp/bestsellers?tag=x&node=1"), amazon_tag=TAG
    )
    assert res.url == "https://www.amazon.es/gp/bestsellers?node=1"
    assert res.warnings == (NOT_AFFILIABLE,)


def test_rewrite_generic_removes_affiliate_param():
    res = rewrite_affiliate_link(
        canonicalize("https://tienda.com/p?aff_id=9&color=red"), amazon_tag=TAG
    )
    assert res.url == "https://tienda.com/p?color=red"
    assert THIRD_PARTY_AFFILIATE_REMOVED in res.warnings
    assert NOT_AFFILIABLE in res.warnings


def test_rewrite_generic_tracking_only_has_no_third_party_warning():
    res = rewrite_affiliate_link(
        canonicalize("https://tienda.com/p?utm_source=x&color=red"), amazon_tag=TAG
    )
    assert res.warnings == (NOT_AFFILIABLE,)


def test_rewrite_generic_tag_param_counts_for_non_amazon():
    res = rewrite_affiliate_link(canonicalize("https://tienda.com/p?tag=zz"), amazon_tag=TAG)
    assert THIRD_PARTY_AFFILIATE_REMOVED in res.warnings
    assert res.url == "https://tienda.com/p"


@pytest.mark.parametrize(
    "host",
    [
        "bit.ly", "www.bit.ly", "tinyurl.com", "t.co", "s.click.aliexpress.com", "amzlink.to",
        "goo.gl", "ow.ly", "buff.ly", "rebrand.ly", "shorturl.at", "cutt.ly", "is.gd",
        "BIT.LY",
    ],
)
def test_generic_shorteners_are_detected(host):
    from app.modules.affiliates.domain.links import is_generic_shortener_host

    assert is_generic_shortener_host(host)


@pytest.mark.parametrize(
    "host", ["amazon.es", "amzn.to", "amzn.eu", "a.co", "pccomponentes.com", "aliexpress.com"]
)
def test_direct_and_amazon_short_hosts_are_not_generic_shorteners(host):
    from app.modules.affiliates.domain.links import is_generic_shortener_host

    assert not is_generic_shortener_host(host)


def test_ensure_not_shortened_raises_spanish_400():
    from app.modules.affiliates.domain.links import ensure_not_shortened

    with pytest.raises(InvalidLinkError) as exc:
        ensure_not_shortened(canonicalize("https://bit.ly/3abc"))
    assert str(exc.value) == "Pega el enlace directo del producto, sin acortadores"
    ensure_not_shortened(canonicalize("https://www.amazon.es/dp/B0ABCDEFGH"))
