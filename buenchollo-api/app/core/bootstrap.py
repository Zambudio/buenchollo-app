"""Raíz de composición: conecta los suscriptores del bus de eventos
(`app.core.events`). Es el único sitio que conoce qué módulo escucha a cuál.

Lo llaman los dos procesos que emiten eventos: la API (`app.main`) y el
scheduler dedicado (`app.run_scheduler`). Es idempotente.

Para añadir una red nueva (p. ej. X o Threads): crear su módulo con un
suscriptor de `DealPostPublished` y registrarlo aquí; Telegram no cambia.
"""

from app.core import events


def register_subscribers() -> None:
    from app.modules.instagram.application.subscriber import on_deal_post_published
    from app.modules.telegram.application.admin_alerts import send_admin_alert
    from app.modules.whatsapp.application.subscriber import on_deal_post_published as queue_for_whatsapp

    events.subscribe(events.DealPostPublished, on_deal_post_published)
    events.subscribe(events.DealPostPublished, queue_for_whatsapp)
    events.subscribe(events.AdminAlert, send_admin_alert)
