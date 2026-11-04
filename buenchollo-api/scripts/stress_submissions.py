"""Prueba de estrés de los endpoints de propuestas de chollos de usuarios.

Uso (desde buenchollo-api/, con la API arrancada y RATE_LIMIT_ENABLED=true):

    python scripts/stress_submissions.py --base-url http://localhost:8010 \\
        --token-file tokens.json --concurrency 50 [--api-pid 1234]

`--token-file`: JSON con una lista de access tokens de Supabase (o un token por
línea) de usuarios de prueba NO admin con el perfil completo. Se usan 5.

Escenarios (cada uno empieza tras `--cooldown` segundos para que la ventana
del rate limit por IP esté limpia):
  a) 50 check-link concurrentes        -> solo 200/429, ningún 5xx, p50/p95
  b) 20 creaciones del MISMO producto  -> exactamente 1 pending, resto 409/429
  c) 30 subidas de imagen (~1 MB PNG)  -> ningún 5xx, latencias y memoria
  d) ráfaga por encima de los límites  -> 429 con Retry-After

Al terminar borra lo que ha creado (propuestas en BD e imágenes en Storage) y
comprueba que no queda nada; si algo no se puede borrar lo imprime. Necesita el
`.env` del backend (DATABASE_URL, SUPABASE_URL, SUPABASE_KEY).
"""
import argparse
import asyncio
import base64
import json
import os
import statistics
import struct
import sys
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=True)

DEFAULT_PRODUCT_URL = "https://www.amazon.es/dp/B09B8X9RGM"
BUCKET = "deal-images"
BUCKET_MARKER = f"/storage/v1/object/public/{BUCKET}/"


def load_tokens(path: str) -> list[str]:
    raw = Path(path).read_text(encoding="utf-8").strip()
    if raw.startswith("["):
        return [t for t in json.loads(raw) if t]
    return [line.strip() for line in raw.splitlines() if line.strip()]


def token_user_id(token: str) -> str:
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))["sub"]


def noise_png(width: int = 600, height: int = 560) -> bytes:
    """PNG RGB con ruido (incompresible): ~1 MB con el tamaño por defecto."""
    rows = b"".join(b"\x00" + os.urandom(width * 3) for _ in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(kind + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows, 1))
        + chunk(b"IEND", b"")
    )


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(pct / 100 * len(ordered)) - 1))
    return ordered[index]


class ProcessMemory:
    """RSS del proceso de la API (y sus hijos: en Windows el python del venv
    lanza el intérprete real como proceso hijo). Requiere psutil (opcional)."""

    def __init__(self, pid: int | None) -> None:
        self.proc = None
        if pid:
            try:
                import psutil

                self.proc = psutil.Process(pid)
            except Exception as exc:  # psutil ausente o PID inválido
                print(f"  (memoria no disponible: {exc})")

    def rss_mb(self) -> float | None:
        if self.proc is None:
            return None
        procs = [self.proc] + self.proc.children(recursive=True)
        total = 0
        for p in procs:
            try:
                total += p.memory_info().rss
            except Exception:
                pass
        return round(total / 2**20, 1)


class Stress:
    def __init__(self, args: argparse.Namespace, tokens: list[str]) -> None:
        self.base = args.base_url.rstrip("/") + "/v1"
        self.tokens = tokens
        self.sem = asyncio.Semaphore(args.concurrency)
        self.product_url = args.product_url
        self.category_id = args.category_id
        self.cooldown = args.cooldown
        self.memory = ProcessMemory(args.api_pid)
        self.created_submissions: set[str] = set()
        self.uploaded_urls: set[str] = set()
        self.results: dict[str, dict] = {}
        self.failures: list[str] = []
        self.missing_retry_after = 0
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(90.0))

    def headers(self, i: int) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.tokens[i % len(self.tokens)]}"}

    async def request(self, method: str, path: str, i: int, **kw) -> tuple[int, float, httpx.Response | None]:
        async with self.sem:
            start = time.perf_counter()
            try:
                resp = await self.client.request(method, self.base + path, headers=self.headers(i), **kw)
            except httpx.HTTPError as exc:
                print(f"  error de red: {type(exc).__name__}: {exc}")
                return -1, (time.perf_counter() - start) * 1000, None
            elapsed = (time.perf_counter() - start) * 1000
        if resp.status_code == 429 and not resp.headers.get("Retry-After"):
            self.missing_retry_after += 1
        return resp.status_code, elapsed, resp

    def summarize(self, name: str, outcomes: list[tuple[int, float, httpx.Response | None]]) -> dict:
        codes: dict[str, int] = {}
        for code, _, _ in outcomes:
            codes[str(code)] = codes.get(str(code), 0) + 1
        ok_lat = [ms for code, ms, _ in outcomes if 200 <= code < 300]
        all_lat = [ms for _, ms, _ in outcomes]
        summary = {
            "requests": len(outcomes),
            "status_codes": dict(sorted(codes.items())),
            "p50_ms": round(statistics.median(all_lat), 1) if all_lat else 0,
            "p95_ms": round(percentile(all_lat, 95), 1),
            "p50_ok_ms": round(statistics.median(ok_lat), 1) if ok_lat else 0,
            "p95_ok_ms": round(percentile(ok_lat, 95), 1),
            "max_ms": round(max(all_lat), 1) if all_lat else 0,
        }
        self.results[name] = summary
        print(f"  {name}: {json.dumps(summary)}")
        return summary

    def expect(self, condition: bool, message: str) -> None:
        print(f"  [{'OK' if condition else 'FAIL'}] {message}")
        if not condition:
            self.failures.append(message)

    async def wait_window(self, label: str) -> None:
        if self.cooldown > 0:
            print(f"\n... esperando {self.cooldown}s (ventana del rate limit) antes de {label}")
            await asyncio.sleep(self.cooldown)

    async def resolve_category(self) -> None:
        if self.category_id:
            return
        resp = await self.client.get(self.base + "/categories")
        resp.raise_for_status()
        self.category_id = resp.json()[0]["id"]

    async def scenario_a(self) -> None:
        print("\n(a) 50 check-link concurrentes")
        outcomes = await asyncio.gather(
            *(self.request("POST", "/submissions/check-link", i, json={"url": self.product_url}) for i in range(50))
        )
        s = self.summarize("a_check_link", outcomes)
        bad = {c for c in s["status_codes"] if c not in ("200", "429")}
        self.expect(not bad, f"solo 200/429 (otros: {sorted(bad) or 'ninguno'})")
        self.expect(not any(c.startswith("5") for c in s["status_codes"]), "ningún 5xx")

    async def scenario_b(self) -> None:
        print("\n(b) 20 creaciones concurrentes del mismo producto con 5 usuarios")
        body = {
            "url": self.product_url,
            "title": "[STRESS TEST] propuesta concurrente",
            "current_price": 19.99,
            "category_id": self.category_id,
            "images": [],
        }
        outcomes = await asyncio.gather(*(self.request("POST", "/submissions", i, json=body) for i in range(20)))
        for code, _, resp in outcomes:
            if code == 201 and resp is not None:
                self.created_submissions.add(resp.json()["id"])
        s = self.summarize("b_create_same_product", outcomes)
        codes = s["status_codes"]
        bad = {c for c in codes if c not in ("201", "409", "429")}
        self.expect(codes.get("201", 0) == 1, f"exactamente 1 respuesta 201 (hubo {codes.get('201', 0)})")
        self.expect(not bad, f"resto 409/429 (otros: {sorted(bad) or 'ninguno'})")
        pending = await count_pending(self.product_url)
        self.results["b_create_same_product"]["pending_in_db"] = pending
        self.expect(pending == 1, f"exactamente 1 propuesta pending en BD para el producto (hay {pending})")

    async def scenario_c(self) -> None:
        print("\n(c) 30 subidas de imagen concurrentes (~1 MB PNG)")
        image = noise_png()
        print(f"  tamaño PNG: {len(image) / 2**20:.2f} MB")
        before = self.memory.rss_mb()
        peak = before
        done = asyncio.Event()

        async def sample() -> None:
            nonlocal peak
            while not done.is_set():
                value = self.memory.rss_mb()
                if value is not None and (peak is None or value > peak):
                    peak = value
                await asyncio.sleep(0.2)

        sampler = asyncio.create_task(sample())
        outcomes = await asyncio.gather(
            *(
                self.request("POST", "/submissions/images", i, files={"file": (f"stress-{i}.png", image, "image/png")})
                for i in range(30)
            )
        )
        done.set()
        await sampler
        for code, _, resp in outcomes:
            if code == 200 and resp is not None:
                self.uploaded_urls.add(resp.json()["url"])
        s = self.summarize("c_image_uploads", outcomes)
        await asyncio.sleep(3)
        after = self.memory.rss_mb()
        s.update({"rss_before_mb": before, "rss_peak_mb": peak, "rss_after_mb": after})
        print(f"  memoria API (RSS MB): antes={before} pico={peak} después={after}")
        self.expect(not any(c.startswith("5") or c == "-1" for c in s["status_codes"]), "ningún 5xx ni error de red")

    async def scenario_d(self) -> None:
        print("\n(d) ráfaga por encima de los límites (check-link 20/min, imágenes 30/min)")
        tiny = noise_png(32, 32)
        outcomes = await asyncio.gather(
            *(self.request("POST", "/submissions/check-link", i, json={"url": self.product_url}) for i in range(30)),
            *(
                self.request("POST", "/submissions/images", i, files={"file": ("burst.png", tiny, "image/png")})
                for i in range(40)
            ),
        )
        for code, _, resp in outcomes:
            if code == 200 and resp is not None and "url" in resp.json():
                self.uploaded_urls.add(resp.json()["url"])
        s = self.summarize("d_burst", outcomes)
        limited = [resp for code, _, resp in outcomes if code == 429 and resp is not None]
        retry_after = sorted({resp.headers.get("Retry-After") for resp in limited})
        s["retry_after_values"] = retry_after
        self.expect(len(limited) >= 20, f"al menos 20 respuestas 429 (hubo {len(limited)})")
        self.expect(bool(limited) and all(r.headers.get("Retry-After") for r in limited),
                    f"todas las 429 llevan Retry-After (valores: {retry_after})")
        self.expect(not any(c.startswith("5") for c in s["status_codes"]), "ningún 5xx")

    async def run(self) -> int:
        self.started_at = datetime.now(timezone.utc)
        await self.resolve_category()
        print(f"API: {self.base} | usuarios: {len(self.tokens)} | producto: {self.product_url}")
        print(f"memoria API inicial (RSS MB): {self.memory.rss_mb()}")
        try:
            await self.wait_window("(a)")
            await self.scenario_a()
            await self.wait_window("(b)")
            await self.scenario_b()
            await self.wait_window("(c)")
            await self.scenario_c()
            await self.wait_window("(d)")
            await self.scenario_d()
            self.expect(self.missing_retry_after == 0,
                        f"ninguna 429 sin Retry-After en toda la ejecución ({self.missing_retry_after})")
        finally:
            await self.client.aclose()
            leftovers = await cleanup(
                [token_user_id(t) for t in self.tokens], self.started_at,
                self.created_submissions, self.uploaded_urls,
            )
            self.results["cleanup"] = leftovers
        print("\nRESUMEN:", json.dumps(self.results, ensure_ascii=False, indent=1))
        if self.failures:
            print("\nFALLOS:\n- " + "\n- ".join(self.failures))
        if leftovers["submissions_left"] or leftovers["storage_left"]:
            print("\nRESTOS SIN BORRAR:", json.dumps(leftovers, indent=1))
            return 2
        return 1 if self.failures else 0


async def count_pending(product_url: str) -> int:
    from sqlalchemy import func, select

    from app.core.database import AsyncSessionLocal
    from app.modules.affiliates.domain.links import canonicalize, extract_url
    from app.modules.products.infrastructure.amazon_client import extract_asin_from_url
    from app.modules.submissions.domain.models import DealSubmission

    import_models()
    link = canonicalize(extract_url(product_url), asin=extract_asin_from_url(product_url))
    cond = DealSubmission.canonical_url == link.canonical_url
    if link.asin:
        cond = cond | (DealSubmission.asin == link.asin)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(func.count()).select_from(DealSubmission).where(DealSubmission.status == "pending", cond)
        )
        return int(result.scalar_one())


def import_models() -> None:
    import app.modules.categories.domain.models  # noqa: F401
    import app.modules.deals.domain.models  # noqa: F401
    import app.modules.stores.domain.models  # noqa: F401
    import app.modules.users.domain.models  # noqa: F401


def storage_path(url: str) -> str | None:
    return url.split(BUCKET_MARKER, 1)[1] if BUCKET_MARKER in url else None


async def cleanup(user_ids: list[str], since: datetime, submission_ids: set[str], urls: set[str]) -> dict:
    from sqlalchemy import or_, select

    from app.core.config import get_settings
    from app.core.database import AsyncSessionLocal
    from app.core.security import get_supabase_client
    from app.modules.submissions.domain.models import DealSubmission

    import_models()
    print("\nLimpieza...")
    async with AsyncSessionLocal() as session:
        query = select(DealSubmission).where(
            or_(
                DealSubmission.id.in_(submission_ids or {"00000000-0000-0000-0000-000000000000"}),
                (DealSubmission.user_id.in_(user_ids)) & (DealSubmission.created_at >= since),
            )
        )
        rows = (await session.execute(query)).scalars().all()
        for row in rows:
            urls.update(u for u in (row.images or []) if storage_path(u))
            await session.delete(row)
        await session.commit()
        left = (await session.execute(query)).scalars().all()
    print(f"  propuestas borradas: {len(rows)} | restantes: {len(left)}")

    paths = sorted({p for p in (storage_path(u) for u in urls) if p})
    storage = get_supabase_client(get_settings()).storage.from_(BUCKET)
    for i in range(0, len(paths), 100):
        storage.remove(paths[i : i + 100])
    remaining = []
    by_folder: dict[str, set[str]] = {}
    for path in paths:
        folder, name = path.rsplit("/", 1)
        by_folder.setdefault(folder, set()).add(name)
    for folder, names in by_folder.items():
        listed = {obj["name"] for obj in storage.list(folder, {"limit": 1000})}
        remaining += [f"{folder}/{n}" for n in sorted(names & listed)]
    print(f"  imágenes borradas de Storage: {len(paths) - len(remaining)} | restantes: {len(remaining)}")
    return {
        "submissions_deleted": len(rows),
        "submissions_left": [str(r.id) for r in left],
        "storage_deleted": len(paths) - len(remaining),
        "storage_left": remaining,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--token-file", required=True)
    parser.add_argument("--concurrency", type=int, default=50)
    parser.add_argument("--api-pid", type=int, default=None, help="PID de la API para medir memoria (psutil)")
    parser.add_argument("--product-url", default=DEFAULT_PRODUCT_URL,
                        help="Producto real que NO esté publicado ni en revisión")
    parser.add_argument("--category-id", default=None)
    parser.add_argument("--cooldown", type=int, default=61, help="Segundos de espera entre escenarios")
    args = parser.parse_args()
    tokens = load_tokens(args.token_file)
    if len(tokens) < 5:
        parser.error("se necesitan al menos 5 tokens de usuarios de prueba")
    return asyncio.run(Stress(args, tokens[:5]).run())


if __name__ == "__main__":
    sys.exit(main())
