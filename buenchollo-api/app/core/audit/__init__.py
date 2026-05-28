"""Audit log de acciones admin críticas."""
from app.core.audit.models import AuditLog
from app.core.audit.service import audit_log

__all__ = ["AuditLog", "audit_log"]
