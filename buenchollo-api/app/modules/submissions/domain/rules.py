from app.core.exceptions import TooManyRequestsError
from app.modules.users.domain.models import Profile

MAX_PENDING_PER_USER = 5
MAX_PER_DAY = 15
MAX_IMAGES = 8
MAX_FEATURES_IN_DESCRIPTION = 10


def is_profile_complete(profile: Profile | None) -> bool:
    return bool(profile and profile.display_name and profile.display_name.strip())


def features_to_markdown(features: list[str]) -> str:
    lines = [f"- {f.strip()}" for f in features if f and f.strip()]
    return "\n".join(lines[:MAX_FEATURES_IN_DESCRIPTION])


def ensure_quota(pending: int, last_24h: int) -> None:
    if pending >= MAX_PENDING_PER_USER:
        raise TooManyRequestsError(
            f"Ya tienes {MAX_PENDING_PER_USER} chollos pendientes de revisión. "
            "Espera a que los revisemos o retira alguno."
        )
    if last_24h >= MAX_PER_DAY:
        raise TooManyRequestsError(
            f"Has alcanzado el límite de {MAX_PER_DAY} propuestas en 24 horas. Inténtalo más tarde."
        )
