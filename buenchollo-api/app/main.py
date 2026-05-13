"""FastAPI entrypoint for the BuenChollo backend."""

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.modules.products.api.router import router as products_router


settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title=settings.app_name)
app.include_router(products_router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Return a small status payload for uptime checks."""
    return {"status": "ok", "app": settings.app_name, "environment": settings.app_env}

