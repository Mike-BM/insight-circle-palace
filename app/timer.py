import random
from datetime import datetime, timedelta

def compute_unlock_at() -> datetime:
    """
    Returns a datetime that is between 60 to 120 minutes in the future.
    """
    delay_minutes = random.randint(60, 120)
    return datetime.utcnow() + timedelta(minutes=delay_minutes)
