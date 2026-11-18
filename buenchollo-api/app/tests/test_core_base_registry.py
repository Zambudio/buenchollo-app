"""`app.core.base` debe registrar todos los modelos de `app/modules/*/domain/models.py`.

Si falta alguno, `alembic revision --autogenerate` generaría un `drop_table`
de sus tablas. Se ejecuta en un proceso aislado porque en el proceso de pytest
otros tests ya han importado los modelos.
"""
import subprocess
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[2]

_SCRIPT = """
import importlib
from pathlib import Path

from app.core.base import Base

registradas = set(Base.metadata.tables)
for models_py in sorted(Path("app/modules").glob("*/domain/models.py")):
    importlib.import_module(".".join(models_py.with_suffix("").parts))

faltan = sorted(set(Base.metadata.tables) - registradas)
print(",".join(faltan))
"""


def test_base_registra_todos_los_modelos_de_dominio():
    result = subprocess.run(
        [sys.executable, "-c", _SCRIPT],
        cwd=API_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "", f"Tablas no registradas en app.core.base: {result.stdout.strip()}"
