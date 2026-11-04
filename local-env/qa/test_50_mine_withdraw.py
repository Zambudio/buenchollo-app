"""Mis chollos: listado propio, aislamiento entre usuarios y retirar propuestas."""

import uuid

import pytest

from conftest import assert_no_5xx, db, detail, submission_payload


@pytest.fixture
def own_submission(pool, category):
    acc = pool.next("create")
    url = f"https://www.pccomponentes.com/qa-mine-{uuid.uuid4().hex[:10]}"
    resp = acc.post("/v1/submissions", json=submission_payload(category, url))
    assert resp.status_code == 201, detail(resp)
    yield acc, resp.json()
    db("DELETE FROM public.deal_submissions WHERE id = $1::uuid", resp.json()["id"])


def test_mine_lists_only_my_submissions(own_submission, users):
    owner, sub = own_submission
    mine = owner.get("/v1/submissions/mine").json()
    assert sub["id"] in [s["id"] for s in mine]
    for other in users:
        if other.id != owner.id:
            assert sub["id"] not in [s["id"] for s in other.get("/v1/submissions/mine").json()]


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "limit=abc", "limit=1e3"])
def test_mine_bad_pagination_is_422(users, query):
    resp = users[0].get(f"/v1/submissions/mine?{query}")
    assert resp.status_code == 422, detail(resp)


def test_mine_pagination_works(users):
    resp = users[0].get("/v1/submissions/mine?limit=1&offset=0")
    assert resp.status_code == 200 and len(resp.json()) <= 1


def test_cannot_withdraw_someone_elses_submission(own_submission, users):
    owner, sub = own_submission
    intruder = next(u for u in users if u.id != owner.id)
    resp = intruder.delete(f"/v1/submissions/{sub['id']}")
    assert resp.status_code in (403, 404), detail(resp)
    assert db("SELECT status FROM public.deal_submissions WHERE id = $1::uuid", sub["id"])[0]["status"] == "pending"


def test_withdraw_then_withdraw_again(own_submission):
    owner, sub = own_submission
    first = owner.delete(f"/v1/submissions/{sub['id']}")
    assert first.status_code == 204, detail(first)
    assert db("SELECT status FROM public.deal_submissions WHERE id = $1::uuid", sub["id"])[0]["status"] == "withdrawn"
    second = owner.delete(f"/v1/submissions/{sub['id']}")
    assert_no_5xx(second)
    assert second.status_code in (404, 409), detail(second)


def test_withdrawn_product_can_be_resubmitted(own_submission, category, pool):
    owner, sub = own_submission
    pool.reserve(owner, "create", 1)
    assert owner.delete(f"/v1/submissions/{sub['id']}").status_code == 204
    again = owner.post("/v1/submissions", json=submission_payload(category, sub["original_url"]))
    assert again.status_code == 201, detail(again)
    db("DELETE FROM public.deal_submissions WHERE id = $1::uuid", again.json()["id"])


@pytest.mark.parametrize("sid", ["no-es-uuid", "00000000-0000-0000-0000-000000000000", "1' OR '1'='1", "%00"])
def test_withdraw_garbage_ids_never_500(users, sid):
    resp = users[0].delete(f"/v1/submissions/{sid}")
    assert_no_5xx(resp)
    assert resp.status_code in (404, 422), detail(resp)
