"""Bus de eventos (`app.core.events`) y su raíz de composición (`app.core.bootstrap`)."""

import subprocess
import sys
from pathlib import Path

import pytest

from app.core import events

API_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def clean_bus():
    saved = {k: list(v) for k, v in events._handlers.items()}
    events.clear()
    yield
    events.clear()
    for k, handlers in saved.items():
        for h in handlers:
            events.subscribe(k, h)


@pytest.mark.asyncio
async def test_entrega_en_orden_a_sincronos_y_asincronos(clean_bus):
    seen = []

    def sync_handler(event):
        seen.append(("sync", event.text))

    async def async_handler(event):
        seen.append(("async", event.text))

    events.subscribe(events.AdminAlert, sync_handler)
    events.subscribe(events.AdminAlert, async_handler)
    events.subscribe(events.AdminAlert, sync_handler)  # idempotente

    await events.publish(events.AdminAlert("hola"))

    assert seen == [("sync", "hola"), ("async", "hola")]


@pytest.mark.asyncio
async def test_un_suscriptor_que_falla_no_afecta_al_emisor_ni_a_los_demas(clean_bus):
    seen = []

    async def boom(event):
        raise RuntimeError("caído")

    events.subscribe(events.AdminAlert, boom)
    events.subscribe(events.AdminAlert, lambda e: seen.append(e.text))

    await events.publish(events.AdminAlert("sigue"))  # no lanza

    assert seen == ["sigue"]


@pytest.mark.asyncio
async def test_sin_suscriptores_no_pasa_nada(clean_bus):
    await events.publish(events.DealPostPublished(session=None, channel_id="c", text="t"))


def test_bootstrap_conecta_instagram_whatsapp_y_los_avisos_al_admin(clean_bus):
    from app.core.bootstrap import register_subscribers
    from app.modules.instagram.application.subscriber import on_deal_post_published
    from app.modules.telegram.application.admin_alerts import send_admin_alert
    from app.modules.whatsapp.application.subscriber import on_deal_post_published as queue_for_whatsapp

    register_subscribers()
    register_subscribers()  # idempotente

    assert events.subscribers(events.DealPostPublished) == [on_deal_post_published, queue_for_whatsapp]
    assert events.subscribers(events.AdminAlert) == [send_admin_alert]


@pytest.mark.parametrize("module", ["app.main", "app.run_scheduler"])
def test_los_dos_procesos_registran_los_suscriptores(module):
    # En un proceso aparte: la API (al importarse) y el scheduler dedicado (al
    # arrancar) deben dejar conectado el bus, o Instagram no publicaría.
    script = f"""
import importlib
from app.core import events
m = importlib.import_module("{module}")
if "{module}" == "app.run_scheduler":
    import app.run_scheduler as rs
    rs.build_deals_scheduler = lambda s: (_ for _ in ()).throw(SystemExit(0))
    try:
        rs.main()
    except SystemExit:
        pass
print(len(events.subscribers(events.DealPostPublished)), len(events.subscribers(events.AdminAlert)))
"""
    result = subprocess.run([sys.executable, "-c", script], cwd=API_ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.strip().splitlines()[-1] == "2 1"
