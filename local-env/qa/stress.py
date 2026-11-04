"""Prueba de estrés contra el entorno local (`bct-local.ps1 stress`).

Escenarios (ninguno debe dar 5xx):
  A. Lectura pública: ráfaga concurrente sobre listados, fichas y categorías.
  B. Web SSR: páginas renderizadas por Vite/TanStack bajo concurrencia.
  C. check-link: todos los usuarios de prueba a la vez, al borde de su límite.
  D. Carrera de creación: todos proponen el MISMO producto a la vez → 1 pendiente.
  E. Subida concurrente de imágenes (~1 MB) y memoria de la API.
  F. Carrera de aprobación: 5 propuestas × 4 aprobaciones simultáneas → 1 chollo cada una.
  G. Inundación de un usuario: 100 check-link a la vez → solo 200/429.
  H. La API sigue sana (/health/ready) mientras hay carga mixta.

Todo lo que crea se borra al terminar (base local; las imágenes del Storage
real se borran con `bct-local.ps1 users delete`).
"""

from __future__ import annotations

import asyncio
import io
import os
import random
import sys
import time
import uuid
from pathlib import Path

import httpx
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "py"))

import test_users  # noqa: E402
from conftest import API, _cleanup, db, submission_payload  # noqa: E402


async def adb(query: str, *args):
    """db() es síncrono (asyncio.run): aquí se ejecuta en un hilo."""
    return await asyncio.to_thread(db, query, *args)


async def acleanup(ids: list[str]) -> None:
    await asyncio.to_thread(_cleanup, ids)

WEB = os.environ.get("BCT_QA_WEB", "http://localhost:8080")
RESULTS: list[tuple[str, bool, str]] = []


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    return values[min(len(values) - 1, int(round(p / 100 * (len(values) - 1))))]


def report(name: str, outcomes: list[tuple[int, float]], ok: bool, extra: str = "") -> None:
    codes: dict[int, int] = {}
    for c, _ in outcomes:
        codes[c] = codes.get(c, 0) + 1
    lat = [t for _, t in outcomes]
    line = (f"{name}: {len(outcomes)} peticiones · códigos {dict(sorted(codes.items()))} · "
            f"p50 {pct(lat, 50) * 1000:.0f} ms · p95 {pct(lat, 95) * 1000:.0f} ms · máx {max(lat or [0]) * 1000:.0f} ms"
            + (f" · {extra}" if extra else ""))
    RESULTS.append((name, ok, line))
    print(("✓ " if ok else "✗ ") + line, flush=True)


async def timed(client: httpx.AsyncClient, method: str, url: str, **kw) -> tuple[int, float, httpx.Response | None]:
    start = time.perf_counter()
    try:
        resp = await client.request(method, url, **kw)
        return resp.status_code, time.perf_counter() - start, resp
    except httpx.HTTPError as exc:
        print(f"   error de red: {type(exc).__name__}: {exc}", flush=True)
        return 599, time.perf_counter() - start, None


def no_5xx(outcomes) -> bool:
    return all(c < 500 for c, _ in outcomes)


def api_rss_mb() -> float | None:
    try:
        import psutil
    except ImportError:
        return None
    pid_file = Path(os.environ.get("LOCALAPPDATA", "")) / "BuenCholloLocal" / "pids" / "api.pid"
    if not pid_file.exists():
        return None
    root = psutil.Process(int(pid_file.read_text().strip()))
    procs = [root, *root.children(recursive=True)]
    return sum(p.memory_info().rss for p in procs if p.is_running()) / 2**20


async def window_reset(label: str) -> None:
    print(f"   (esperando 62 s para limpiar la ventana del rate limit antes de {label})", flush=True)
    await asyncio.sleep(62)


async def scenario_a(client: httpx.AsyncClient) -> None:
    slugs = [r["slug"] for r in await adb("SELECT slug FROM public.deals WHERE status = 'active' LIMIT 40")]
    paths = ["/v1/deals?limit=24", "/v1/deals/page?limit=24", "/v1/deals/latest", "/v1/deals/popular",
             "/v1/categories", "/health"] + [f"/v1/deals/{s}" for s in slugs]
    sem = asyncio.Semaphore(60)

    async def one():
        async with sem:
            return await timed(client, "GET", API + random.choice(paths))

    outs = [(c, t) for c, t, _ in await asyncio.gather(*[one() for _ in range(600)])]
    report("A. Lectura pública (600, conc. 60)", outs, no_5xx(outs) and all(c == 200 for c, _ in outs))


async def scenario_b(client: httpx.AsyncClient) -> None:
    slug = (await adb("SELECT slug FROM public.deals WHERE status = 'active' LIMIT 1"))[0]["slug"]
    pages = ["/", f"/chollo/{slug}", "/publicar", "/blog"]
    await timed(client, "GET", WEB + "/")  # calentar Vite
    sem = asyncio.Semaphore(10)

    async def one():
        async with sem:
            return await timed(client, "GET", WEB + random.choice(pages))

    outs = [(c, t) for c, t, _ in await asyncio.gather(*[one() for _ in range(80)])]
    report("B. Web SSR (80, conc. 10)", outs, no_5xx(outs))


async def scenario_c(client, tokens) -> None:
    async def one(tok):
        return await timed(client, "POST", f"{API}/v1/submissions/check-link",
                           headers={"Authorization": f"Bearer {tok}"},
                           json={"url": f"https://www.pccomponentes.com/stress-{uuid.uuid4().hex[:8]}"})

    outs = [(c, t) for c, t, _ in await asyncio.gather(*[one(tok) for tok in tokens for _ in range(19)])]
    report(f"C. check-link {len(tokens)} usuarios × 19 a la vez", outs, all(c == 200 for c, _ in outs))


async def scenario_d(client, tokens, category) -> None:
    ok = True
    outs_all = []
    for round_ in range(3):
        url = f"https://www.pccomponentes.com/stress-race-{round_}-{uuid.uuid4().hex[:8]}"
        body = submission_payload(category, url)

        async def one(tok):
            return await timed(client, "POST", f"{API}/v1/submissions",
                               headers={"Authorization": f"Bearer {tok}"}, json=body)

        outs = await asyncio.gather(*[one(tok) for tok in tokens for _ in range(3)])
        outs_all += [(c, t) for c, t, _ in outs]
        created = sum(1 for c, _, _ in outs if c == 201)
        pending = (await adb("SELECT count(*) AS n FROM public.deal_submissions WHERE original_url = $1 AND status = 'pending'",
                     url))[0]["n"]
        ok &= created == 1 and pending == 1 and all(c in (201, 409) for c, _, _ in outs)
        if not (created == 1 and pending == 1):
            print(f"   ronda {round_}: creadas {created}, pendientes en BD {pending}", flush=True)
    report(f"D. Mismo producto × {len(tokens) * 3} a la vez (3 rondas)", outs_all, ok,
           "exactamente 1 pendiente por ronda" if ok else "DUPLICADOS")


def noise_png(seed: int) -> bytes:
    rnd = random.Random(seed)
    img = Image.frombytes("RGB", (600, 560), bytes(rnd.getrandbits(8) for _ in range(600 * 560 * 3)))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def scenario_e(client, tokens) -> None:
    blobs = [noise_png(i) for i in range(5)]
    before = api_rss_mb()

    async def one(tok, i):
        return await timed(client, "POST", f"{API}/v1/submissions/images",
                           headers={"Authorization": f"Bearer {tok}"},
                           files={"file": (f"s{i}.png", blobs[i % 5], "image/png")})

    outs = [(c, t) for c, t, _ in await asyncio.gather(*[one(tok, i) for tok in tokens for i in range(5)])]
    after = api_rss_mb()
    mem = f"memoria API {before:.0f} → {after:.0f} MB" if before and after else ""
    report(f"E. {len(outs)} imágenes de ~{len(blobs[0]) // 1024} KB a la vez", outs,
           all(c == 200 for c, _ in outs), mem)


async def scenario_f(client, tokens, admin_token, category) -> None:
    subs = []
    for i, tok in enumerate(tokens[1:6]):
        resp = await client.post(f"{API}/v1/submissions", headers={"Authorization": f"Bearer {tok}"},
                                 json=submission_payload(category, f"https://www.pccomponentes.com/stress-ap-{uuid.uuid4().hex[:8]}"))
        assert resp.status_code == 201, resp.text
        subs.append(resp.json())

    async def approve(sub):
        body = {"title": sub["title"], "affiliate_url": sub["affiliate_url"], "current_price": sub["current_price"],
                "previous_price": sub["previous_price"], "category_id": sub["category_id"],
                "subcategory_id": sub["subcategory_id"], "store_id": sub["store_id"], "status": "active"}
        return await timed(client, "POST", f"{API}/v1/admin/submissions/{sub['id']}/approve",
                           headers={"Authorization": f"Bearer {admin_token}"}, json=body)

    outs = await asyncio.gather(*[approve(s) for s in subs for _ in range(4)])
    deals = (await adb("SELECT count(*) AS n FROM public.deal_submissions s JOIN public.deals d ON d.id = s.deal_id "
               "WHERE s.id = ANY($1::uuid[])", [s["id"] for s in subs]))[0]["n"]
    oks = sum(1 for c, _, _ in outs if c == 200)
    ok = oks == len(subs) and deals == len(subs) and all(c in (200, 409) for c, _, _ in outs)
    report(f"F. {len(subs)} propuestas × 4 aprobaciones simultáneas", [(c, t) for c, t, _ in outs], ok,
           f"{oks} aprobadas, {deals} chollos creados")


async def scenario_g(client, token) -> None:
    async def one():
        return await timed(client, "POST", f"{API}/v1/submissions/check-link",
                           headers={"Authorization": f"Bearer {token}"},
                           json={"url": "https://www.pccomponentes.com/stress-flood"})

    outs = await asyncio.gather(*[one() for _ in range(100)])
    codes = [c for c, _, _ in outs]
    retry = all(r.headers.get("Retry-After") for c, _, r in outs if c == 429 and r is not None)
    ok = set(codes) <= {200, 429} and codes.count(200) == 20 and retry
    report("G. Un usuario lanza 100 check-link a la vez", [(c, t) for c, t, _ in outs], ok,
           f"{codes.count(200)} aceptadas (límite 20/min), 429 con Retry-After: {retry}")


async def scenario_h(client, tokens) -> None:
    stop = asyncio.Event()
    health: list[tuple[int, float]] = []

    async def probe():
        while not stop.is_set():
            c, t, _ = await timed(client, "GET", f"{API}/health/ready")
            health.append((c, t))
            await asyncio.sleep(0.25)

    async def load():
        jobs = []
        for tok in tokens:
            hdr = {"Authorization": f"Bearer {tok}"}
            for _ in range(4):
                jobs.append(timed(client, "POST", f"{API}/v1/submissions/images/from-url", headers=hdr,
                                  json={"url": "https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png"}))
            for _ in range(10):
                jobs.append(timed(client, "GET", f"{API}/v1/deals?limit=24"))
        return await asyncio.gather(*jobs)

    prober = asyncio.create_task(probe())
    outs = await load()
    stop.set()
    await prober
    ok = no_5xx([(c, t) for c, t, _ in outs]) and all(c == 200 for c, _ in health)
    report("H. /health/ready durante carga mixta", health, ok,
           f"carga: {sorted({c for c, _, _ in outs})}")


async def main() -> int:
    accounts = test_users._load()
    if len(accounts) < 6:
        print("Hacen falta 6 usuarios de prueba: .\\local-env\\bct-local.ps1 users create 6")
        return 2
    ids = [a["id"] for a in accounts]
    tokens = await test_users.tokens()
    admin_token, user_tokens = tokens[0], tokens[1:]
    cat = (await adb("SELECT c.id::text AS id, (SELECT s.id::text FROM public.categories s WHERE s.parent_id = c.id LIMIT 1) AS sub "
             "FROM public.categories c WHERE c.parent_id IS NULL AND c.is_active "
             "AND EXISTS (SELECT 1 FROM public.categories s WHERE s.parent_id = c.id) LIMIT 1"))[0]
    category = {"category_id": cat["id"], "subcategory_id": cat["sub"]}

    await acleanup(ids)
    await adb("INSERT INTO public.user_roles (user_id, role) VALUES ($1, 'admin') ON CONFLICT DO NOTHING", ids[0])
    limits = httpx.Limits(max_connections=200, max_keepalive_connections=50)
    try:
        async with httpx.AsyncClient(timeout=120, limits=limits) as client:
            await scenario_a(client)
            await scenario_b(client)
            await scenario_c(client, tokens)
            await window_reset("D")
            await scenario_d(client, tokens, category)
            await acleanup(ids)
            await scenario_e(client, tokens)
            await window_reset("F")
            await scenario_f(client, tokens, admin_token, category)
            await window_reset("G")
            await scenario_g(client, user_tokens[0])
            await window_reset("H")
            await scenario_h(client, tokens)
    finally:
        await adb("DELETE FROM public.user_roles WHERE user_id = $1 AND role = 'admin'", ids[0])
        await acleanup(ids)

    print("\nResumen:")
    for name, ok, _ in RESULTS:
        print(f"  {'OK ' if ok else 'FALLO'} {name}")
    return 0 if all(ok for _, ok, _ in RESULTS) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
