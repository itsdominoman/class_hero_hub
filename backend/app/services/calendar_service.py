from datetime import datetime, date, timedelta
from typing import List, Tuple
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from .. import models

def get_family_now(family_timezone: str) -> datetime:
    return datetime.now(ZoneInfo(family_timezone))

def get_family_today(family_timezone: str) -> date:
    return get_family_now(family_timezone).date()

def get_week_bounds(ref_date: date, week_start_day: int) -> Tuple[date, date]:
    """
    Returns (start_date, end_date) for the week containing ref_date.
    week_start_day: 0=Monday, 6=Sunday (matches date.weekday())
    """
    # Calculate days to subtract to get to the week_start_day
    # (ref_date.weekday() - week_start_day) % 7 gives the offset from start of week
    days_from_start = (ref_date.weekday() - week_start_day) % 7
    start_date = ref_date - timedelta(days=days_from_start)
    end_date = start_date + timedelta(days=6)
    return start_date, end_date

def get_bonus_date(week_start_date: date) -> date:
    """
    The bonus day is the first day of the NEXT week.
    """
    return week_start_date + timedelta(days=7)

def resolve_occurrences(entry: models.CalendarEntry, from_date: date, to_date: date) -> List[date]:
    """
    Resolves a CalendarEntry definition into a list of actual dates (occurrences) 
    between from_date and to_date (inclusive).
    """
    occurrences = []
    
    if entry.recurrence_type == "none":
        if from_date <= entry.start_date <= to_date:
            occurrences.append(entry.start_date)
        return occurrences

    # For recurring tasks, we start from the entry's start_date or from_date, whichever is later.
    current = max(entry.start_date, from_date)
    
    # Pre-parse recurrence_days if weekly
    recurrence_days_list = []
    if entry.recurrence_type == "weekly" and entry.recurrence_days:
        try:
            recurrence_days_list = [int(d.strip()) for d in entry.recurrence_days.split(",") if d.strip()]
        except ValueError:
            pass

    while current <= to_date:
        if entry.recurrence_type == "daily":
            occurrences.append(current)
        elif entry.recurrence_type == "weekly":
            if current.weekday() in recurrence_days_list:
                occurrences.append(current)
        
        current += timedelta(days=1)
        
    return occurrences
