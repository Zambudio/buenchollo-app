"""Paso 2: el formulario. Datos válidos, todos los errores de usuario, duplicados y cupos."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from conftest import assert_no_5xx, db, detail, submission_payload


def store_url(tag: str) -> str:
    return f"https://www.pccomponentes.com/qa-{tag}-{uuid.uuid4().hex[:10]}"


def create(pool, body):
    acc = pool.next("create")
    return acc, acc.post("/v1/submissions", json=body)


def drop(submission_id: str) -> None:
    db("DELETE FROM public.deal_submissions WHERE id = $1::uuid", submission_id)


@pytest.fixture
def uploaded_image(pool):
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (640, 480), (20, 120, 200)).save(buf, format="PNG")
    acc = pool.next("images")
    resp = acc.post("/v1/submissions/images", files={"file": ("p.png", buf.getvalue(), "image/png")})
    assert resp.status_code == 200, detail(resp)
    return resp.json()["url"]


# ── Casos válidos ──────────────────────────────────────────────────────────


def test_minimal_valid_submission(pool, category, mail):
    url = store_url("min")
    acc, resp = create(pool, submission_payload(category, url, previous_price=None, description=None))
    assert resp.status_code == 201, detail(resp)
    data = resp.json()
    assert data["status"] == "pending"
    assert data["store_name"] == "PcComponentes"
    assert data["original_url"].startswith("https://www.pccomponentes.com/qa-min-")
    # Aviso al admin en el capturador de correo local.
    msg = mail.wait_for(lambda m: data["title"] in (m["html"] + m["text"] + (m["subject"] or ""))
                        or "propuesta" in (m["subject"] or "").lower())
    assert msg["to"]
    drop(data["id"])


def test_full_submission_with_images_coupon_dates(pool, category, uploaded_image):
    now = datetime.now(timezone.utc)
    body = submission_payload(
        category,
        store_url("full"),
        title="  Portátil Ñandú «edición» 💻 — 16\" 32GB  ",
        description="Línea 1\n- punto\n**negrita**",
        current_price="1299.00",
        previous_price="1499.99",
        coupon_code="  VERANO10 ",
        shipping_info="Envío gratis",
        starts_at=(now + timedelta(days=1)).isoformat(),
        expires_at=(now + timedelta(days=7)).isoformat(),
        images=[uploaded_image],
        image_url=uploaded_image,
    )
    acc, resp = create(pool, body)
    assert resp.status_code == 201, detail(resp)
    data = resp.json()
    assert data["title"] == "Portátil Ñandú «edición» 💻 — 16\" 32GB"
    assert data["coupon_code"] == "VERANO10"
    assert data["images"] == [uploaded_image]
    assert data["current_price"] == 1299.0
    drop(data["id"])


def test_amazon_submission_gets_our_affiliate_tag(pool, category):
    acc, resp = create(
        pool,
        submission_payload(category, "https://www.amazon.es/dp/B0BF5M2K9B?tag=competencia-21&th=1"),
    )
    assert resp.status_code == 201, detail(resp)
    data = resp.json()
    assert data["asin"] == "B0BF5M2K9B"
    assert "tag=buenchollo0b-21" in data["affiliate_url"]
    assert "competencia" not in data["affiliate_url"]
    drop(data["id"])


def test_html_and_sql_in_text_are_stored_literally(pool, category):
    evil = "<script>alert('x')</script>'; DROP TABLE deals;--"
    acc, resp = create(pool, submission_payload(category, store_url("xss"), title=evil[:200], description=evil))
    assert resp.status_code in (201, 422), detail(resp)
    if resp.status_code == 201:
        assert resp.json()["title"] == evil[:200]
        drop(resp.json()["id"])
    assert db("SELECT count(*) AS n FROM public.deals")[0]["n"] > 0


# ── Errores de usuario en el formulario ────────────────────────────────────

FUTURE = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
PAST = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()


@pytest.mark.parametrize(
    "overrides",
    [
        {"title": ""},
        {"title": "    "},
        {"title": "x" * 201},
        {"current_price": "0"},
        {"current_price": "-5"},
        {"current_price": "abc"},
        {"current_price": "100001"},
        {"current_price": "19.999"},
        {"current_price": None},
        {"previous_price": "19.99"},
        {"previous_price": "10"},
        {"previous_price": "-1"},
        {"expires_at": PAST},
        {"starts_at": FUTURE, "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()},
        {"expires_at": "mañana"},
        {"category_id": "no-es-uuid"},
        {"category_id": ""},
        {"category_id": None},
        {"coupon_code": "C" * 65},
        {"shipping_info": "s" * 121},
        {"store_name": "t" * 81},
        {"description": "d" * 10_001},
        {"images": ["https://evil.example.com/a.jpg"]},
        {"images": ["http://m.media-amazon.com/images/I/a.jpg"]},
        {"images": ["https://ltekgqeqgzvrkfhsmxvy.supabase.co/storage/v1/object/public/deal-images/submissions/../../avatars/x.png"]},
        {"images": ["javascript:alert(1)"]},
        {"images": [f"https://m.media-amazon.com/images/I/{i}.jpg" for i in range(9)]},
        {"images": [], "image_url": "https://m.media-amazon.com/images/I/a.jpg"},
        {"images": "https://m.media-amazon.com/images/I/a.jpg"},
        {"url": "https://bit.ly/abc"},
        {"url": "texto sin enlace"},
        {"url": ""},
    ],
    ids=lambda o: ",".join(f"{k}={str(v)[:25]}" for k, v in o.items()),
)
def test_invalid_form_values_get_4xx(pool, category, overrides):
    body = submission_payload(category, store_url("bad"))
    body.update(overrides)
    acc, resp = create(pool, body)
    assert_no_5xx(resp)
    assert 400 <= resp.status_code < 500, detail(resp)
    if resp.status_code == 201:  # no debería pasar, pero no dejar basura
        drop(resp.json()["id"])


def test_unknown_category_uuid_is_rejected(pool, category):
    body = submission_payload(category, store_url("cat"), category_id=str(uuid.uuid4()), subcategory_id=None)
    acc, resp = create(pool, body)
    assert_no_5xx(resp)
    assert 400 <= resp.status_code < 500, detail(resp)


def test_subcategory_from_another_category_is_rejected(pool, category):
    other = db(
        "SELECT s.id::text AS id FROM public.categories s WHERE s.parent_id IS NOT NULL "
        "AND s.parent_id <> $1::uuid LIMIT 1",
        category["category_id"],
    )[0]["id"]
    body = submission_payload(category, store_url("sub"), subcategory_id=other)
    acc, resp = create(pool, body)
    assert_no_5xx(resp)
    assert 400 <= resp.status_code < 500, detail(resp)


def test_extra_fields_cannot_set_status_or_owner(pool, category, admin):
    body = submission_payload(category, store_url("extra"), status="approved", user_id=admin.id,
                              deal_id=str(uuid.uuid4()), affiliate_url="https://evil.example.com")
    acc, resp = create(pool, body)
    assert resp.status_code in (201, 422), detail(resp)
    if resp.status_code == 201:
        data = resp.json()
        assert data["status"] == "pending"
        assert "evil" not in data["affiliate_url"]
        row = db("SELECT user_id::text AS u, deal_id FROM public.deal_submissions WHERE id = $1::uuid", data["id"])[0]
        assert row["u"] == acc.id and row["deal_id"] is None
        drop(data["id"])


# ── Duplicados ─────────────────────────────────────────────────────────────


def test_same_product_twice_while_pending_is_409(pool, category):
    url = store_url("dup")
    acc1, first = create(pool, submission_payload(category, url))
    assert first.status_code == 201, detail(first)
    # Mismo producto con otra forma de URL (query + mayúsculas en host).
    acc2, second = create(pool, submission_payload(category, url.replace("www.pccomponentes.com", "WWW.PcComponentes.com") + "?utm_source=x"))
    assert_no_5xx(second)
    assert second.status_code == 409, detail(second)
    # Y el paso 1 lo marca como "en revisión".
    check = pool.next("check").post("/v1/submissions/check-link", json={"url": url})
    assert check.json()["status"] == "in_review", detail(check)
    drop(first.json()["id"])


def test_same_amazon_asin_via_different_urls_is_409(pool, category):
    acc, first = create(pool, submission_payload(category, "https://www.amazon.es/dp/B0C1H26C46"))
    assert first.status_code == 201, detail(first)
    acc, second = create(pool, submission_payload(category, "https://www.amazon.es/Cualquier-Nombre/dp/B0C1H26C46/ref=x"))
    assert second.status_code == 409, detail(second)
    drop(first.json()["id"])


# ── Cupos por usuario ──────────────────────────────────────────────────────


def test_sixth_pending_submission_is_429_with_message(pool, users, category):
    acc = users[4]
    pool.reserve(acc, "create", 6)
    created = []
    try:
        for i in range(5):
            resp = acc.post("/v1/submissions", json=submission_payload(category, store_url(f"cupo{i}")))
            assert resp.status_code == 201, detail(resp)
            created.append(resp.json()["id"])
        resp = acc.post("/v1/submissions", json=submission_payload(category, store_url("cupo6")))
        assert resp.status_code == 429, detail(resp)
        assert "pendientes" in detail(resp)
    finally:
        for sid in created:
            drop(sid)
