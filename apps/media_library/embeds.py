"""Turn a pasted YouTube / Vimeo link into a safe embed URL (or "" if we don't recognise it).

Only fixed, well-known player hosts are ever produced, so a leader can't inject an
arbitrary iframe source by pasting a link.
"""
import re
from urllib.parse import parse_qs, urlparse

_YT_ID = re.compile(r"[A-Za-z0-9_-]{11}")


def embed_url(url: str) -> str:
    if not url:
        return ""
    try:
        parts = urlparse(url.strip())
    except ValueError:
        return ""
    if parts.scheme not in ("http", "https"):
        return ""
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]

    video_id = ""
    if host in ("youtube.com", "m.youtube.com"):
        if parts.path == "/watch":
            video_id = parse_qs(parts.query).get("v", [""])[0]
        else:
            segs = parts.path.split("/")
            if len(segs) > 2 and segs[1] in ("embed", "live", "shorts"):
                video_id = segs[2]
    elif host == "youtu.be":
        video_id = parts.path.lstrip("/").split("/")[0]
    if _YT_ID.fullmatch(video_id or ""):
        return f"https://www.youtube-nocookie.com/embed/{video_id}"

    if host == "vimeo.com":
        m = re.fullmatch(r"/(\d+)", parts.path)
        if m:
            return f"https://player.vimeo.com/video/{m.group(1)}"
    return ""
