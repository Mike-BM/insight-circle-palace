"""Single shared rate limiter for the whole API.

Behind Vercel (or any reverse proxy) `request.client.host` is the proxy, not the visitor,
so the default key function would put every user in one bucket. We read the real client IP
from the proxy headers instead.

NOTE: the default in-memory storage is per server instance. On serverless platforms
(Vercel) each instance keeps its own counters, so limits are only approximate. For strict
limits set RATE_LIMIT_STORAGE_URI to a shared store, e.g. a Redis/Upstash URL:
    RATE_LIMIT_STORAGE_URI=rediss://default:<password>@<host>:6379
"""

import os

from slowapi import Limiter
from starlette.requests import Request


def client_ip(request: Request) -> str:
    for header in ("x-vercel-forwarded-for", "x-real-ip", "x-forwarded-for"):
        value = request.headers.get(header)
        if value:
            return value.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(
    key_func=client_ip,
    storage_uri=(os.environ.get("RATE_LIMIT_STORAGE_URI") or "").strip() or None,
)
