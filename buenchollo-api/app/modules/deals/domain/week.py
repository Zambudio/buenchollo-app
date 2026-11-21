"""La «semana» de los chollos: los 7 días naturales que acaban hoy, en hora de
Madrid. La comparten el ranking «Top de la semana» de la web y el resumen
«Los chollos de la semana» de los domingos, para que siempre coincidan."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")


@dataclass(frozen=True)
class WeekWindow:
    first_day: date
    last_day: date
    since: datetime  # medianoche (Madrid) del primer día


def week_window(now: datetime) -> WeekWindow:
    last_day = now.astimezone(MADRID).date()
    first_day = last_day - timedelta(days=6)
    return WeekWindow(first_day, last_day, datetime.combine(first_day, time.min, tzinfo=MADRID))
