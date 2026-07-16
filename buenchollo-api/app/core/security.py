import logging
from dataclasses import dataclass

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from app.core.config import get_settings, Settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

logger = logging.getLogger(__name__)

security = HTTPBearer()

# Algoritmos asimétricos que Supabase publica en su JWKS. La clave es pública,
# así que verificar la firma en local no requiere ningún secreto adicional.
_ASYMMETRIC_ALGS = ("ES256", "RS256")

# Audiencia estándar de los access tokens de Supabase Auth.
_SUPABASE_AUD = "authenticated"

# Cliente JWKS module-level: PyJWKClient cachea las claves públicas, de modo
# que solo hay red hacia Supabase en el primer request y al expirar la caché
# (1h), no en cada validación. Ver ADR-010 / AUDIT_REPORT H-02.
_jwks_client: PyJWKClient | None = None


@dataclass(frozen=True)
class AuthenticatedUser:
    """Usuario autenticado mínimo extraído de los claims del JWT.

    Expone la misma superficie que usan los routers del objeto de gotrue
    (`.id` y `.email`), de forma que el cambio a validación local es
    transparente para el resto de la aplicación.
    """

    id: str
    email: str | None = None


def _clean_supabase_url(settings: Settings) -> str:
    # Limpiar URL de forma defensiva por si contiene /rest/v1/
    return settings.supabase_url.split("/rest/v1")[0].rstrip("/")


def get_supabase_client(settings: Settings = Depends(get_settings)) -> Client:
    """Provee un cliente de Supabase instanciado."""
    return create_client(_clean_supabase_url(settings), settings.supabase_key)


def _get_jwks_client(settings: Settings) -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(
            f"{_clean_supabase_url(settings)}/auth/v1/.well-known/jwks.json",
            cache_keys=True,
            lifespan=3600,
        )
    return _jwks_client


def _decode_local(token: str, settings: Settings) -> dict | None:
    """Verifica el JWT en local (firma + expiración + audiencia).

    Devuelve los claims si el token es verificable con el material de firma
    disponible, o `None` si no hay forma de verificarlo en local (p. ej.
    HS256 sin `SUPABASE_JWT_SECRET` configurado, o JWKS inaccesible) — en
    ese caso el caller hace fallback a la validación remota de Supabase.
    Lanza `jwt.InvalidTokenError` (y subclases) si el token es INVÁLIDO.
    """
    header = jwt.get_unverified_header(token)  # InvalidTokenError si malformado
    alg = header.get("alg")

    if alg in _ASYMMETRIC_ALGS:
        try:
            key = _get_jwks_client(settings).get_signing_key_from_jwt(token).key
        except jwt.PyJWKClientError as exc:
            # JWKS no disponible o kid desconocido: no podemos verificar en
            # local. Mejor degradar a validación remota que tumbar la API.
            logger.warning("JWKS no disponible, fallback a validación remota: %s", exc)
            return None
        return jwt.decode(token, key, algorithms=[alg], audience=_SUPABASE_AUD)

    if alg == "HS256" and settings.supabase_jwt_secret:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience=_SUPABASE_AUD,
        )

    # Algoritmo no soportado en local (o HS256 sin secreto): fallback remoto.
    return None


def _get_user_via_supabase(token: str, settings: Settings) -> AuthenticatedUser:
    """Validación remota (red de seguridad): pregunta a Supabase por el token."""
    supabase = create_client(_clean_supabase_url(settings), settings.supabase_key)
    user_response = supabase.auth.get_user(token)
    if not user_response or not user_response.user:
        raise ValueError("Supabase devolvió respuesta vacía para el token")
    return AuthenticatedUser(id=str(user_response.user.id), email=user_response.user.email)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
) -> AuthenticatedUser:
    """
    Valida el token JWT y devuelve el usuario autenticado.

    La firma se verifica EN LOCAL contra la clave pública del JWKS de
    Supabase (o `SUPABASE_JWT_SECRET` si el proyecto usara HS256), evitando
    un round-trip HTTP a Supabase por request. Si no hay material de firma
    disponible se degrada a la validación remota de siempre.
    Falla con 401 si el token es inválido o expiró.
    """
    token = credentials.credentials
    try:
        claims = _decode_local(token, settings)
        if claims is None:
            user = _get_user_via_supabase(token, settings)
        else:
            sub = claims.get("sub")
            if not sub:
                raise jwt.InvalidTokenError("token sin claim 'sub'")
            user = AuthenticatedUser(id=str(sub), email=claims.get("email"))
        # Loguear sólo user_id (UUID, no es PII directa). El email queda
        # fuera del log para no filtrar PII si alguien deja LOG_LEVEL=DEBUG
        # en producción. Ver SECURITY_AUDIT.md SEC-09.
        logger.debug("JWT validado OK — user_id=%s", user.id)
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("JWT inválido o expirado: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def require_admin(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Verifica que el usuario actual tenga rol de administrador
    consultando directamente la tabla user_roles.
    """
    user_id = str(current_user.id)
    try:
        result = await db.execute(
            text("SELECT 1 FROM user_roles WHERE user_id::text = :user_id AND role = 'admin' LIMIT 1"),
            {"user_id": user_id},
        )
        is_admin = result.scalar() is not None
        logger.debug("Comprobación admin — user_id=%s is_admin=%s", user_id, is_admin)

        if not is_admin:
            logger.warning("Acceso admin denegado para user_id=%s", user_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos de administrador"
            )
        return current_user
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error al verificar rol admin para user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al verificar privilegios de administrador",
        )
