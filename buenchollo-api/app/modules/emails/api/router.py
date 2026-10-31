"""Endpoints de la API para gestión y envío de correos electrónicos."""
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from supabase import Client

from app.core.security import get_current_user, get_supabase_client
from app.modules.emails.application.welcome_service import WelcomeEmailService
from app.modules.emails.infrastructure.smtp import get_email_sender

router = APIRouter(tags=["emails"])


class WelcomeEmailRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=50)


def get_welcome_service(
    supabase: Client = Depends(get_supabase_client),
) -> WelcomeEmailService:
    return WelcomeEmailService(
        sender=get_email_sender(),
        supabase_client=supabase,
    )


@router.post("/auth/welcome", status_code=status.HTTP_200_OK)
async def send_welcome_email_endpoint(
    payload: WelcomeEmailRequest | None = None,
    current_user=Depends(get_current_user),
    service: WelcomeEmailService = Depends(get_welcome_service),
) -> dict:
    """Envía el correo de bienvenida al usuario recién registrado/autenticado.

    Garantiza idempotencia: si ya se envió anteriormente, no repite el envío.
    """
    if not current_user.email:
        return {"success": False, "sent": False, "message": "El usuario no tiene email registrado"}

    name = payload.display_name if payload else None
    sent = await service.send_welcome_if_needed(
        user_id=str(current_user.id),
        email=current_user.email,
        name=name,
    )
    return {
        "success": True,
        "sent": sent,
        "message": "Correo de bienvenida enviado" if sent else "Correo ya enviado anteriormente o no requerido",
    }
