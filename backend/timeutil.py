from datetime import datetime, timedelta, timezone
from typing import Optional


def now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def now_iso() -> str:
    return to_iso(now())


def parse(value: Optional[str]) -> datetime:
    # py3.9 fromisoformat cannot parse a trailing Z
    if not value:
        return now()
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return now()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def hours_between(earlier: str, later: str) -> float:
    return (parse(later) - parse(earlier)).total_seconds() / 3600.0


def hours_since(value: str, reference: Optional[datetime] = None) -> float:
    return ((reference or now()) - parse(value)).total_seconds() / 3600.0


def ago(hours: float = 0.0, minutes: float = 0.0) -> str:
    return to_iso(now() - timedelta(hours=hours, minutes=minutes))
