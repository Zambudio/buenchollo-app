"""Rate limit por usuario: el que abusa recibe 429 con Retry-After; los demás no se ven afectados."""

import uuid

from conftest import detail, submission_payload


def test_check_link_burst_gets_429_with_retry_after(pool, users):
    abuser, bystander = users[3], users[2]
    pool.drain(abuser, "check")
    codes = []
    last = None
    for _ in range(25):
        last = abuser.post("/v1/submissions/check-link", json={"url": "https://www.pccomponentes.com/qa-rl"})
        codes.append(last.status_code)
    pool.reserve(abuser, "check", 19)
    assert codes[:20] == [200] * 20, codes
    assert set(codes[20:]) == {429}, codes
    assert last.headers.get("Retry-After"), last.headers
    assert "detail" in last.json()
    pool.reserve(bystander, "check", 1)
    other = bystander.post("/v1/submissions/check-link", json={"url": "https://www.pccomponentes.com/qa-rl2"})
    assert other.status_code == 200, detail(other)


def test_create_burst_gets_429(pool, users, category):
    abuser = users[3]
    pool.drain(abuser, "create")
    codes = []
    for _ in range(12):
        # Cuerpo inválido a propósito: también cuenta para el límite y no deja basura.
        resp = abuser.post("/v1/submissions", json=submission_payload(
            category, f"https://www.pccomponentes.com/qa-{uuid.uuid4().hex[:6]}", current_price="0"))
        codes.append(resp.status_code)
    pool.reserve(abuser, "create", 9)
    assert codes[:10] == [422] * 10, codes
    assert set(codes[10:]) == {429}, codes
