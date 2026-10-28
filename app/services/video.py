import re
from typing import Optional

DRIVE_FILE_ID_PATTERNS = [
    r"drive\.google\.com\/file\/d\/([a-zA-Z0-9_-]{20,})",
    r"drive\.google\.com\/open\?(?:.*&)?id=([a-zA-Z0-9_-]{20,})",
    r"drive\.google\.com\/uc\?(?:.*&)?id=([a-zA-Z0-9_-]{20,})",
    r"docs\.google\.com\/file\/d\/([a-zA-Z0-9_-]{20,})",
    r"^([a-zA-Z0-9_-]{25,60})$",
]


def extract_drive_file_id(url_or_id: Optional[str]) -> Optional[str]:
    """
    Extracts and validates a Google Drive file ID from standard sharing URLs
    or direct ID strings.
    """
    if not url_or_id:
        return None
    cleaned = url_or_id.strip()
    for pattern in DRIVE_FILE_ID_PATTERNS:
        match = re.search(pattern, cleaned)
        if match:
            return match.group(1)
    return None


def format_drive_embed_url(file_id: str) -> str:
    """
    Returns the standard responsive iframe preview embed URL for Google Drive.
    """
    return f"https://drive.google.com/file/d/{file_id}/preview"


async def generate_signed_storage_url(
    bucket: str, file_path: str, expires_in_seconds: int = 3600
) -> Optional[str]:
    """
    Generates a short-lived signed URL for private Supabase Storage objects.
    Ensures video assets stored in private buckets cannot be downloaded or streamed
    permanently without authorized session verification.
    """
    import os
    import urllib.request
    import json

    supabase_url = os.environ.get("SUPABASE_URL")
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")

    if not supabase_url or not service_role_key:
        return None

    api_endpoint = f"{supabase_url.rstrip('/')}/storage/v1/object/sign/{bucket}/{file_path.lstrip('/')}"
    req = urllib.request.Request(
        api_endpoint,
        data=json.dumps({"expiresIn": expires_in_seconds}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {service_role_key}",
            "apikey": service_role_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                body = json.loads(response.read().decode("utf-8"))
                signed_url_path = body.get("signedURL")
                if signed_url_path:
                    if signed_url_path.startswith("http"):
                        return signed_url_path
                    return f"{supabase_url.rstrip('/')}/storage/v1{signed_url_path}"
    except Exception as e:
        print(f"Warning: Failed to generate signed storage URL: {e}")

    return None


async def resolve_secure_playback_url(
    video_source_type: str,
    drive_file_id: Optional[str] = None,
    video_url: Optional[str] = None,
) -> str:
    """
    Resolves the authoritative streaming or embed URL based on storage source.
    Generates short-lived signed URLs for private Supabase storage when configured.
    """
    if video_source_type == "google_drive" and drive_file_id:
        return format_drive_embed_url(drive_file_id)

    if video_source_type in ["supabase_storage", "private_storage"] and video_url:
        # Check if URL format is bucket/path
        parts = video_url.strip().split("/", 1)
        if len(parts) == 2:
            bucket, path = parts
            signed = await generate_signed_storage_url(bucket, path)
            if signed:
                return signed

    if video_url:
        return video_url

    return ""

