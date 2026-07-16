"""Tests de la validación local de JWT (ADR-010 / AUDIT_REPORT H-02).

Verifican que `get_current_user` valida firma, expiración y audiencia EN
LOCAL (sin red): tokens ES256 firmados con una clave de test se aceptan solo
si la firma coincide con la clave pública "publicada", y cualquier token
inválido produce 401. El fallback remoto solo debe activarse cuando no hay
material de firma local (p. ej. HS256 sin secreto configurado).
"""
import time
from types import SimpleNamespace
from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ec import SECP256R1, generate_private_key
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core import security
from app.core.config import Settings

# Par de claves EC efímero que simula la clave de firma de Supabase.
_PRIVATE_KEY = generate_private_key(SECP256R1())
_PUBLIC_KEY = _PRIVATE_KEY.public_key()
# Una segunda clave para simular un atacante firmando con otra clave.
_ATTACKER_KEY = generate_private_key(SECP256R1())

_SETTINGS = Settings(supabase_url="https://test.supabase.co", supabase_key="dummy")


def _token(
    *,
    key=_PRIVATE_KEY,
    alg: str = "ES256",
    sub: str = "11111111-2222-3333-4444-555555555555",
    aud: str = "authenticated",
    email: str = "user@test.dev",
    exp_offset: int = 3600,
) -> str:
    claims = {"sub": sub, "aud": aud, "email": email, "exp": int(time.time()) + exp_offset}
    return jwt.encode(claims, key, algorithm=alg)


class _FakeJWKSClient:
    """Sustituye a PyJWKClient devolviendo la clave pública de test."""

    def get_signing_key_from_jwt(self, token: str):
        return SimpleNamespace(key=_PUBLIC_KEY)


def _credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


@pytest.fixture(autouse=True)
def _jwks_local():
    """Todas las pruebas usan el JWKS falso — cero red."""
    with patch.object(security, "_get_jwks_client", return_value=_FakeJWKSClient()):
        yield


async def _call(token: str):
    return await security.get_current_user(_credentials(token), _SETTINGS)


@pytest.mark.asyncio
async def test_token_es256_valido_devuelve_usuario():
    user = await _call(_token())
    assert user.id == "11111111-2222-3333-4444-555555555555"
    assert user.email == "user@test.dev"


@pytest.mark.asyncio
async def test_token_expirado_devuelve_401():
    with pytest.raises(HTTPException) as exc:
        await _call(_token(exp_offset=-60))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_firma_de_otra_clave_devuelve_401():
    with pytest.raises(HTTPException) as exc:
        await _call(_token(key=_ATTACKER_KEY))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_audiencia_incorrecta_devuelve_401():
    with pytest.raises(HTTPException) as exc:
        await _call(_token(aud="anon"))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_token_sin_sub_devuelve_401():
    claims = {"aud": "authenticated", "exp": int(time.time()) + 3600}
    token = jwt.encode(claims, _PRIVATE_KEY, algorithm="ES256")
    with pytest.raises(HTTPException) as exc:
        await _call(token)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_token_basura_devuelve_401():
    with pytest.raises(HTTPException) as exc:
        await _call("no-soy-un-jwt")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_hs256_con_secreto_configurado_valida_en_local():
    settings = Settings(
        supabase_url="https://test.supabase.co",
        supabase_key="dummy",
        supabase_jwt_secret="super-secreto-de-test",
    )
    claims = {
        "sub": "abc",
        "aud": "authenticated",
        "email": "hs@test.dev",
        "exp": int(time.time()) + 3600,
    }
    token = jwt.encode(claims, "super-secreto-de-test", algorithm="HS256")
    user = await security.get_current_user(_credentials(token), settings)
    assert user.id == "abc"


@pytest.mark.asyncio
async def test_hs256_sin_secreto_hace_fallback_remoto():
    token = jwt.encode(
        {"sub": "abc", "aud": "authenticated", "exp": int(time.time()) + 3600},
        "cualquier-secreto",
        algorithm="HS256",
    )
    fallback_user = security.AuthenticatedUser(id="via-remoto", email=None)
    with patch.object(security, "_get_user_via_supabase", return_value=fallback_user) as mock_remote:
        user = await _call(token)
    mock_remote.assert_called_once()
    assert user.id == "via-remoto"


@pytest.mark.asyncio
async def test_jwks_caido_hace_fallback_remoto_no_500():
    class _BrokenJWKS:
        def get_signing_key_from_jwt(self, token: str):
            raise jwt.PyJWKClientError("JWKS inaccesible")

    fallback_user = security.AuthenticatedUser(id="via-remoto", email=None)
    with (
        patch.object(security, "_get_jwks_client", return_value=_BrokenJWKS()),
        patch.object(security, "_get_user_via_supabase", return_value=fallback_user),
    ):
        user = await _call(_token())
    assert user.id == "via-remoto"
