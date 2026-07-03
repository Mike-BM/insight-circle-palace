from datetime import datetime, timedelta

def compute_unlock_at() -> datetime:
    """
    Returns a datetime that is 1 minute in the future.
    """
    return datetime.utcnow() + timedelta(minutes=1)
