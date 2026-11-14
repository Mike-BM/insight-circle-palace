"""Shared security helpers: environment detection, password policy, safe redirects."""

import os
from urllib.parse import urlparse

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 128

# Small deny-list of the most commonly breached passwords (compared case-insensitively).
# For stronger protection, plug in a breached-password API (e.g. HaveIBeenPwned k-anonymity).
_COMMON_PASSWORDS = {
    "password", "password1", "password12", "password123", "password1234",
    "passw0rd", "p@ssw0rd", "p@ssword", "qwerty", "qwerty123", "qwertyuiop",
    "qwerty1234", "1234567890", "123456789", "12345678", "1234567", "123456",
    "0123456789", "1q2w3e4r5t", "1qaz2wsx", "iloveyou", "iloveyou1", "letmein",
    "letmein123", "welcome", "welcome1", "welcome123", "admin", "admin123",
    "admin1234", "administrator", "changeme", "changeme123", "abc123456",
    "abcd1234", "abcdefghij", "monkey123", "dragon123", "football1", "baseball1",
    "sunshine1", "princess1", "trustno1", "superman1", "master123", "login123",
    "insightcircle", "insightcircle1", "insightcircle123", "insightcirclepalace",
    "kenya123", "nairobi123", "mombasa123", "kenya2024", "kenya2025", "kenya2026",
}


def is_production() -> bool:
    """True on production deployments.

    APP_ENV=production|prod -> production. APP_ENV=development|dev|test|testing|local ->
    not production. If APP_ENV is unset, any Vercel deployment counts as production so a
    missing variable can never silently enable development-only behaviour.
    """
    env = (os.environ.get("APP_ENV") or "").strip().lower()
    if env in ("production", "prod"):
        return True
    if env in ("development", "dev", "test", "testing", "local"):
        return False
    return os.environ.get("VERCEL") == "1" or os.environ.get("VERCEL_ENV") == "production"


def payment_simulation_allowed() -> bool:
    """Simulated M-Pesa / Stripe payments are for local development and CI only."""
    return not is_production()


def validate_password_strength(password: str) -> str:
    """Raise ValueError with a user-friendly message if the password is too weak."""
    if password is None:
        raise ValueError("Password is required.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_LENGTH} characters long.")
    lowered = password.lower()
    if lowered in _COMMON_PASSWORDS:
        raise ValueError("This password is too common. Please choose a less predictable one.")
    if len(set(password)) < 4:
        raise ValueError("Password is too repetitive. Please use a mix of different characters.")
    if password.strip() == "":
        raise ValueError("Password cannot be blank.")
    return password


def safe_redirect_url(candidate, default: str, allowed_base: str) -> str:
    """Return `candidate` only if it is an http(s) URL on the same host as `allowed_base`.

    Prevents callers from supplying an arbitrary success/cancel URL for payment redirects.
    """
    if not candidate:
        return default
    try:
        cand = urlparse(candidate.strip())
        base = urlparse(allowed_base)
    except Exception:
        return default
    if cand.scheme not in ("http", "https") or not cand.netloc:
        return default
    cand_host = cand.hostname or ""
    base_host = base.hostname or ""
    if cand_host == base_host or cand_host == f"www.{base_host}" or f"www.{cand_host}" == base_host:
        return candidate.strip()
    return default
