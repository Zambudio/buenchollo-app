import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from app.core.config import get_settings, Settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

logger = logging.getLogger(__name__)

security = HTTPBearer()

def get_supabase_client(settings: Settings = Depends(get_settings)) -> Client:
    """Provee un cliente de Supabase instanciado."""
    # Limpiar URL de forma defensiva por si contiene /rest/v1/
    url = settings.supabase_url.split("/rest/v1")[0].rstrip("/")
    return create_client(url, settings.supabase_key)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Valida el token JWT contra Supabase y devuelve el usuario.
    Falla con 401 si el token es inválido o expiró.
    """
    try:
        # get_user llama a Supabase para verificar el token JWT de forma segura
        user_response = supabase.auth.get_user(credentials.credentials)
        if not user_response or not user_response.user:
            raise ValueError("Supabase devolvió respuesta vacía para el token")
        # Loguear sólo user_id (UUID, no es PII directa). El email queda
        # fuera del log para no filtrar PII si alguien deja LOG_LEVEL=DEBUG
        # en producción. Ver SECURITY_AUDIT.md SEC-09.
        logger.debug("JWT validado OK — user_id=%s", user_response.user.id)
        return user_response.user
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
