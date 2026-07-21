from app.core.exceptions import ConflictError, NotFoundError, ValidationError


class ScheduledDealNotFound(NotFoundError):
    def __init__(self, identifier: str):
        super().__init__(f"Programacion '{identifier}' no encontrada")


class ScheduledDealNotEditable(ConflictError):
    def __init__(self):
        super().__init__("Solo se pueden modificar programaciones pendientes")


class InvalidSchedule(ValidationError):
    pass
