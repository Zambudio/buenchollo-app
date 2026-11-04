"""Moderación: aprobar, rechazar, carreras entre admins, duplicados y sustitución de caducados."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from conftest import assert_no_5xx, db, detail, submission_payload


def new_pending(pool, category, url=None, **overrides):
    acc = pool.next("create")
    url = url or f"https://www.pccomponentes.com/qa-review-{uuid.uuid4().hex[:10]}"
    resp = acc.post("/v1/submissions", json=submission_payload(category, url, **overrides))
    assert resp.status_code == 201, detail(resp)
    return acc, resp.json()


def deal_body(sub: dict, **overrides) -> dict:
    body = {
        "title": sub["title"],
        "description": sub.get("description"),
        "affiliate_url": sub["affiliate_url"],
        "current_price": sub["current_price"],
        "previous_price": sub.get("previous_price"),
        "category_id": sub.get("category_id"),
        "subcategory_id": sub.get("subcategory_id"),
        "store_id": sub.get("store_id"),
        "images": sub.get("images") or [],
        "image_url": sub.get("image_url"),
        "coupon_code": sub.get("coupon_code"),
        "shipping_info": sub.get("shipping_info"),
        "status": "active",
    }
    body.update(overrides)
    return {k: v for k, v in body.items() if v is not None}


def status_of(sid: str) -> str:
    return db("SELECT status FROM public.deal_submissions WHERE id = $1::uuid", sid)[0]["status"]


def test_approve_publishes_with_author_and_notifies(pool, admin, category, mail, anon):
    owner, sub = new_pending(pool, category, title="QA aprobado ✅", coupon_code="QA10")
    resp = admin.post(f"/v1/admin/submissions/{sub['id']}/approve",
                      json=deal_body(sub, title="QA aprobado ✅ (editado por admin)"))
    assert resp.status_code == 200, detail(resp)
    deal = resp.json()
    assert deal["title"] == "QA aprobado ✅ (editado por admin)"
    row = db("SELECT source, created_by::text AS by, coupon_code FROM public.deals WHERE id = $1::uuid", deal["id"])[0]
    assert row["source"] == "community" and row["by"] == owner.id and row["coupon_code"] == "QA10"
    assert status_of(sub["id"]) == "approved"

    public = anon.get(f"/v1/deals/{deal['slug']}")
    assert public.status_code == 200, detail(public)
    assert (public.json().get("author") or {}).get("display_name"), "la ficha pública debe mostrar el autor"

    mine = owner.get("/v1/submissions/mine").json()
    assert next(s for s in mine if s["id"] == sub["id"])["deal_slug"] == deal["slug"]

    notes = owner.get("/v1/notifications").json()
    assert any(n.get("deal_id") == deal["id"] or deal["slug"] in (n.get("link_url") or "") for n in notes), notes
    mail.wait_for(lambda m: owner.email in (m["to"] or "") and deal["title"][:20] in (m["html"] + m["text"]))


def test_reject_requires_reason_and_notifies(pool, admin, category, mail):
    owner, sub = new_pending(pool, category)
    for bad in ("", "  ", "ok", " a ", "x" * 501):
        resp = admin.post(f"/v1/admin/submissions/{sub['id']}/reject", json={"reason": bad})
        assert_no_5xx(resp)
        assert resp.status_code == 422, f"{bad!r}: {detail(resp)}"
    assert status_of(sub["id"]) == "pending"

    reason = "El precio no es el actual <b>en tienda</b>"
    resp = admin.post(f"/v1/admin/submissions/{sub['id']}/reject", json={"reason": reason})
    assert resp.status_code == 200, detail(resp)
    assert status_of(sub["id"]) == "rejected"
    mine = next(s for s in owner.get("/v1/submissions/mine").json() if s["id"] == sub["id"])
    assert mine["rejection_reason"] == reason
    msg = mail.wait_for(lambda m: owner.email in (m["to"] or "") and "precio no es el actual" in (m["html"] + m["text"]))
    assert "<b>en tienda</b>" not in msg["html"], "el motivo debe ir escapado en el HTML del correo"


def test_decided_submissions_cannot_be_decided_again(pool, admin, category):
    owner, sub = new_pending(pool, category)
    assert admin.post(f"/v1/admin/submissions/{sub['id']}/reject", json={"reason": "No es un chollo"}).status_code == 200
    again = admin.post(f"/v1/admin/submissions/{sub['id']}/approve", json=deal_body(sub))
    assert again.status_code == 409, detail(again)
    twice = admin.post(f"/v1/admin/submissions/{sub['id']}/reject", json={"reason": "Otra vez"})
    assert twice.status_code == 409, detail(twice)
    withdraw = owner.delete(f"/v1/submissions/{sub['id']}")
    assert withdraw.status_code in (404, 409), detail(withdraw)


def test_withdrawn_submission_cannot_be_approved(pool, admin, category):
    owner, sub = new_pending(pool, category)
    assert owner.delete(f"/v1/submissions/{sub['id']}").status_code == 204
    resp = admin.post(f"/v1/admin/submissions/{sub['id']}/approve", json=deal_body(sub))
    assert resp.status_code in (404, 409), detail(resp)
    assert db("SELECT count(*) AS n FROM public.deals WHERE created_by = $1::uuid AND title = $2",
              owner.id, sub["title"])[0]["n"] == 0


@pytest.mark.parametrize("sid", [str(uuid.uuid4()), "no-uuid", "1;DROP TABLE deals"])
def test_unknown_ids_never_500(admin, sid):
    for method, path, kw in (
        ("get", f"/v1/admin/submissions/{sid}", {}),
        ("post", f"/v1/admin/submissions/{sid}/reject", {"json": {"reason": "Motivo válido"}}),
        ("post", f"/v1/admin/submissions/{sid}/approve",
         {"json": {"title": "x", "affiliate_url": "https://www.pccomponentes.com/x", "current_price": 1}}),
    ):
        resp = getattr(admin, method)(path, **kw)
        assert_no_5xx(resp)
        assert resp.status_code in (404, 422), f"{path}: {detail(resp)}"


def test_concurrent_double_click_approve_creates_one_deal(pool, admin, category):
    owner, sub = new_pending(pool, category)
    body = deal_body(sub)
    with ThreadPoolExecutor(10) as ex:
        results = list(ex.map(lambda _: admin.post(f"/v1/admin/submissions/{sub['id']}/approve", json=body), range(10)))
    codes = sorted(r.status_code for r in results)
    assert all(c < 500 for c in codes), codes
    assert codes.count(200) == 1, codes
    n = db("SELECT count(*) AS n FROM public.deals WHERE created_by = $1::uuid AND title = $2", owner.id, sub["title"])[0]["n"]
    assert n == 1


def test_concurrent_approve_and_reject_one_wins(pool, admin, category):
    owner, sub = new_pending(pool, category)
    calls = [
        lambda: admin.post(f"/v1/admin/submissions/{sub['id']}/approve", json=deal_body(sub)),
        lambda: admin.post(f"/v1/admin/submissions/{sub['id']}/reject", json={"reason": "Carrera de admins"}),
    ] * 3
    with ThreadPoolExecutor(6) as ex:
        results = list(ex.map(lambda f: f(), calls))
    ok = [r for r in results if r.status_code == 200]
    assert len(ok) == 1, [r.status_code for r in results]
    assert all(r.status_code < 500 for r in results)


def test_approve_with_other_affiliate_tag_is_rewritten(pool, admin, category):
    owner, sub = new_pending(pool, category, url="https://www.amazon.es/dp/B0D1XD1ZV3")
    resp = admin.post(f"/v1/admin/submissions/{sub['id']}/approve",
                      json=deal_body(sub, affiliate_url="https://www.amazon.es/dp/B0D1XD1ZV3?tag=ajeno-21"))
    assert resp.status_code == 200, detail(resp)
    assert "tag=buenchollo0b-21" in resp.json()["affiliate_url"]
    assert "ajeno" not in resp.json()["affiliate_url"]


def test_approve_with_mismatched_asin_is_rejected(pool, admin, category):
    owner, sub = new_pending(pool, category, url="https://www.amazon.es/dp/B0CHX1W1XY")
    resp = admin.post(f"/v1/admin/submissions/{sub['id']}/approve",
                      json=deal_body(sub, affiliate_url="https://www.amazon.es/dp/B0000000XX"))
    assert_no_5xx(resp)
    assert resp.status_code == 422, detail(resp)
    assert status_of(sub["id"]) == "pending"


@pytest.mark.parametrize("bad", [
    {"affiliate_url": "https://bit.ly/xyz"},
    {"affiliate_url": "no es url"},
    {"current_price": 0},
    {"title": "   "},
    {"status": "lo-que-sea"},
])
def test_approve_with_bad_deal_data_keeps_submission_pending(pool, admin, category, bad):
    owner, sub = new_pending(pool, category)
    resp = admin.post(f"/v1/admin/submissions/{sub['id']}/approve", json=deal_body(sub, **bad))
    assert_no_5xx(resp)
    assert 400 <= resp.status_code < 500, detail(resp)
    assert status_of(sub["id"]) == "pending"


def test_published_product_cannot_be_proposed_again(pool, admin, category):
    owner, sub = new_pending(pool, category)
    first = admin.post(f"/v1/admin/submissions/{sub['id']}/approve", json=deal_body(sub))
    assert first.status_code == 200, detail(first)
    again = pool.next("create").post("/v1/submissions", json=submission_payload(category, sub["original_url"]))
    assert again.status_code == 409, detail(again)
    assert again.json().get("reason") == "published", detail(again)


def test_approve_when_admin_published_it_meanwhile_is_409_and_stays_pending(pool, admin, category):
    """Mientras la propuesta espera, un admin publica el mismo producto a mano."""
    owner, sub = new_pending(pool, category)
    manual = admin.post("/v1/deals/admin", json=deal_body(sub, title="Publicado a mano"))
    assert manual.status_code == 200, detail(manual)
    resp = admin.post(f"/v1/admin/submissions/{sub['id']}/approve", json=deal_body(sub))
    assert resp.status_code == 409, detail(resp)
    assert status_of(sub["id"]) == "pending"
    db("DELETE FROM public.deals WHERE id = $1::uuid", manual.json()["id"])


def test_approving_resubmitted_expired_product_replaces_the_old_deal(pool, admin, category):
    owner, sub = new_pending(pool, category)
    first = admin.post(f"/v1/admin/submissions/{sub['id']}/approve", json=deal_body(sub))
    assert first.status_code == 200, detail(first)
    old_id = first.json()["id"]
    db("UPDATE public.deals SET status = 'expired', expires_at = now() - interval '1 day' WHERE id = $1::uuid", old_id)

    check = pool.next("check").post("/v1/submissions/check-link", json={"url": sub["original_url"]})
    assert check.status_code == 200 and check.json()["status"] == "ok", detail(check)

    owner2, sub2 = new_pending(pool, category, url=sub["original_url"], current_price="9.99")
    resp = admin.post(f"/v1/admin/submissions/{sub2['id']}/approve", json=deal_body(sub2))
    assert resp.status_code == 200, detail(resp)
    assert db("SELECT count(*) AS n FROM public.deals WHERE id = $1::uuid", old_id)[0]["n"] == 0
    assert db("SELECT count(*) AS n FROM public.deals WHERE id = $1::uuid", resp.json()["id"])[0]["n"] == 1


def test_scheduled_approval_is_not_public_yet(pool, admin, category, anon):
    owner, sub = new_pending(pool, category)
    later = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    resp = admin.post(f"/v1/admin/submissions/{sub['id']}/approve",
                      json=deal_body(sub, scheduled_for=later, status="scheduled"))
    assert resp.status_code == 200, detail(resp)
    assert resp.json()["status"] == "scheduled"
    listing = anon.get("/v1/deals?limit=50").json()
    assert resp.json()["id"] not in [d["id"] for d in listing]


def test_admin_queue_shows_author_and_previously_published(pool, admin, category):
    owner, sub = new_pending(pool, category)
    one = admin.get(f"/v1/admin/submissions/{sub['id']}")
    assert one.status_code == 200, detail(one)
    assert one.json()["author"]["display_name"]
    queue = admin.get("/v1/admin/submissions").json()
    assert sub["id"] in [s["id"] for s in queue]
    count = admin.get("/v1/admin/submissions/count").json()
    assert count["pending"] >= 1
