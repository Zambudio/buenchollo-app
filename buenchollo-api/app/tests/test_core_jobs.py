"""Engine/sesión de los jobs de fondo (`app/core/jobs.py`). Sin BD: el engine
no abre conexión hasta la primera consulta."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.pool import NullPool

from app.core import jobs
from app.core.config import Settings

_SETTINGS = Settings(database_url="postgresql+asyncpg://user:pass@localhost/db")


@pytest.mark.asyncio
async def test_job_engine_usa_nullpool_con_opciones_de_pgbouncer_y_lo_libera(monkeypatch):
    captured = {}
    fake_engine = MagicMock()
    fake_engine.dispose = AsyncMock()

    def _fake_create(url, **kwargs):
        captured.update(url=url, **kwargs)
        return fake_engine

    monkeypatch.setattr(jobs, "create_async_engine", _fake_create)

    with pytest.raises(RuntimeError):
        async with jobs.job_engine(_SETTINGS) as engine:
            assert engine is fake_engine
            raise RuntimeError("fallo del job")

    assert captured["url"] == _SETTINGS.database_url
    assert captured["poolclass"] is NullPool
    assert captured["connect_args"] == {"server_settings": {"jit": "off"}, "statement_cache_size": 0}
    fake_engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_job_session_sobre_engine_propio_sin_expirar_al_commit():
    async with jobs.job_session(_SETTINGS) as session:
        assert isinstance(session.bind.pool, NullPool)
        assert session.sync_session.expire_on_commit is False
