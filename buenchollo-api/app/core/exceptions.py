"""Jerarquía base de excepciones de dominio.

El dominio y la capa de aplicación lanzan estas excepciones para comunicar
errores de negocio sin depender de FastAPI (`HTTPException`).

Un único `exception_handler` central en `main.py` se encarga de traducirlas
al status HTTP correspondiente. Esto:

- Separa lógica de negocio del protocolo HTTP (Clean Architecture).
- Centraliza el formato de error de la API (`{"detail": "..."}`).
- Permite reutilizar la lógica desde CLIs, workers o tests sin
  importar FastAPI.

Subclases concretas viven en `app/modules/<modulo>/domain/exceptions.py`.
"""


class DomainError(Exception):
    """Raíz de todos los errores de negocio. No se usa directamente — heredar."""

    #: HTTP status que el handler global devolverá. Subclases lo sobrescriben.
    http_status: int = 500


class NotFoundError(DomainError):
    """Recurso solicitado no existe. → 404."""

    http_status: int = 404


class ForbiddenError(DomainError):
    """El usuario autenticado no tiene permiso para esta operación. → 403."""

    http_status: int = 403


class ConflictError(DomainError):
    """La operación choca con el estado actual del sistema (duplicado, etc.). → 409."""

    http_status: int = 409


class ValidationError(DomainError):
    """Datos de entrada inválidos a nivel de negocio (no de schema). → 400."""

    http_status: int = 400


class ServiceUnavailableError(DomainError):
    """Un servicio externo del que dependemos no está disponible. → 503."""

    http_status: int = 503
