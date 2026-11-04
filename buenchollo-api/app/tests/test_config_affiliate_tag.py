"""M8: sin AMAZON_AFFILIATE_TAG en producción la API no arranca."""
import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize("tag", ["", "   "])
def test_produccion_sin_tag_falla_al_arrancar(tag):
    with pytest.raises(ValidationError, match="AMAZON_AFFILIATE_TAG"):
        Settings(app_env="production", amazon_affiliate_tag=tag)


def test_produccion_con_tag_arranca():
    assert Settings(app_env="production", amazon_affiliate_tag="x-21").amazon_affiliate_tag == "x-21"


def test_local_sin_tag_se_permite():
    assert Settings(app_env="local", amazon_affiliate_tag="").amazon_affiliate_tag == ""
