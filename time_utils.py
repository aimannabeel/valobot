from datetime import datetime, timedelta, timezone

def get_current_week_start():
    now = datetime.now(timezone.utc)

    days_since_sunday = (now.weekday() + 1) % 7

    week_start = now - timedelta(days=days_since_sunday)

    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    return week_start.date().isoformat()


def is_match_in_week(started_at, week_start):
    match_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))

    week_start_time = datetime.fromisoformat(week_start).replace(tzinfo=timezone.utc)
    week_end_time = week_start_time + timedelta(days=7)

    return week_start_time <= match_time < week_end_time