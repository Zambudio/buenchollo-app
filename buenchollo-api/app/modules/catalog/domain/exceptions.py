from app.core.exceptions import NotFoundError


class ProductNotFound(NotFoundError):
    def __init__(self):
        super().__init__("Producto no encontrado")
