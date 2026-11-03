from app.modules.users.domain.models import Profile

MAX_PENDING_PER_USER = 5
MAX_SUBMISSIONS_PER_DAY = 15
MAX_FEATURES_IN_DESCRIPTION = 10


def is_profile_complete(profile: Profile | None) -> bool:
    return bool(profile and profile.display_name and profile.display_name.strip())


def features_to_markdown(features: list[str]) -> str:
    lines = [f"- {f.strip()}" for f in features if f and f.strip()]
    return "\n".join(lines[:MAX_FEATURES_IN_DESCRIPTION])
