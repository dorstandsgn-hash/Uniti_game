"""Определение названия фильма по заголовку, описанию и комментариям."""
import re

_LABEL = re.compile(
    r"(?:название|фильм|сериал|мультфильм|мульт|кино|film|movie|series)"
    r"(?:\s+(?:фильма|сериала|кино))?\s*[:\-–—]\s*(.+)",
    re.IGNORECASE,
)
_QUOTED = re.compile(r"[«\"“]([^»\"”]{2,60})[»\"”]")
_JUNK = re.compile(r"в\s+(?:коммент|описан|закреп|профил)|подпиш|ссылк|телеграм|t\.me",
                   re.IGNORECASE)


def _clean(s):
    s = re.split(r"[#\n|•]", s)[0]
    s = re.sub(r"[^\w\s.,:!?()&'\-+]", "", s)  # эмодзи и прочее
    s = re.sub(r"\s+", " ", s).strip(" .,:-—–")
    return s[:70]


def _from_text(text):
    for line in (text or "").splitlines():
        m = _LABEL.search(line)
        if m:
            name = _clean(m.group(1))
            if len(name) >= 2 and not _JUNK.search(name):
                return name
    m = _QUOTED.search(text or "")
    if m:
        name = _clean(m.group(1))
        if len(name) >= 2 and not _JUNK.search(name):
            return name
    return None


def _from_pipes(title):
    """«Он помог ей 💀 | Knives Out | Песня #shorts» -> «Knives Out»."""
    parts = [_clean(p) for p in (title or "").split("|")]
    if len(parts) >= 3 and len(parts[1]) >= 2:
        return parts[1]
    return None


def find_movie(info):
    """Возвращает название фильма/сериала или None."""
    sources = [info.get("description"), info.get("title")]
    for text in sources:
        name = _from_text(text)
        if name:
            return name
    name = _from_pipes(info.get("title"))
    if name:
        return name
    comments = info.get("comments") or []
    # Сначала закреплённые и комментарии автора, потом самые залайканные
    comments.sort(key=lambda c: (not c.get("is_pinned"),
                                 not c.get("author_is_uploader"),
                                 -(c.get("like_count") or 0)))
    sources = [c.get("text") for c in comments[:15]]
    for text in sources:
        name = _from_text(text)
        if name:
            return name
    # В закреплённом комментарии автора часто пишут только название
    for c in comments[:3]:
        if c.get("is_pinned") or c.get("author_is_uploader"):
            name = _clean(c.get("text") or "")
            if 2 <= len(name) <= 50 and not _JUNK.search(name):
                return name
    return None
