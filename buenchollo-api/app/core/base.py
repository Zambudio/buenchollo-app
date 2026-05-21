"""
Import all models here so Alembic can discover them.
This file should be imported by Alembic's env.py.
"""
from app.core.database import Base

# Import all models to register them with Base.metadata
from app.modules.categories.domain.models import Category
from app.modules.stores.domain.models import Store
from app.modules.users.domain.models import Profile
from app.modules.deals.domain.models import Deal

__all__ = ["Base", "Category", "Store", "Profile", "Deal"]
