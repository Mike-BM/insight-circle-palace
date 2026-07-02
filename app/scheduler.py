import asyncio
from datetime import datetime
from .db import applications

async def sweep_pending_applications():
    """
    Background task that sweeps pending applications every 5 minutes
    and approves them if their unlock_at time has passed.
    """
    while True:
        now = datetime.utcnow()
        for app_id, record in applications.items():
            if record.status == "pending" and now >= record.unlock_at:
                record.status = "approved"
        
        # Sleep for 5 minutes (300 seconds)
        await asyncio.sleep(300)
