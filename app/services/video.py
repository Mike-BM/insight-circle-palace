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
