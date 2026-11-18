"""Garantiza que `.env.example` documenta todas las variables de `Settings`."""
import re
from pathlib import Path

from app.core.config import Settings

ENV_EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"

# Campos de `Settings` que NO son variables de entorno configurables.
# Hoy no hay ninguno (las propiedades `effective_*` no son campos de
# pydantic y no aparecen en `model_fields`); añadir aquí con motivo si surge.
NO_ENV_FIELDS: set[str] = set()


def _env_example_names() -> set[str]:
    names = set()
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Z][A-Z0-9_]*)=", line)
        if m:
            names.add(m.group(1))
    return names


def test_todos_los_campos_de_settings_estan_en_env_example():
    expected = {name.upper() for name in Settings.model_fields} - NO_ENV_FIELDS
    missing = sorted(expected - _env_example_names())
    assert not missing, f"Faltan en .env.example: {missing}"


def test_env_example_no_define_variables_inexistentes():
    expected = {name.upper() for name in Settings.model_fields}
    extra = sorted(_env_example_names() - expected)
    assert not extra, f".env.example define variables que Settings no lee: {extra}"
