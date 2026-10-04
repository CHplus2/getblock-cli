"""Keep resource identifiers inside one URL path segment."""
from urllib.parse import quote, unquote


def path_segment(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("Resource ID must be a nonempty string.")
    probe = value
    while True:
        if probe in (".", "..") or any(c in probe for c in '/\\?#') or any(ord(c) < 32 or ord(c) == 127 for c in probe):
            raise ValueError("Resource ID must be one path segment, without URL separators or traversal.")
        decoded = unquote(probe)
        if decoded == probe:
            break
        probe = decoded
    return quote(value, safe="")
