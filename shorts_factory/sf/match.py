"""Поиск в длинном видео того же места, что и в нарезке-доноре (по репликам)."""
import re
from statistics import median

from rapidfuzz import fuzz


def _norm(text):
    return re.sub(r"[^\w]", "", text.lower().replace("ё", "е"))


def find_offset(ref_words, src_words, threshold):
    """Ищет реплики нарезки в исходнике.

    Возвращает (score, offset): offset — на сколько секунд время в исходнике
    больше времени в нарезке, т.е. начало нарезки = offset.
    """
    ref = [(n, w) for w in ref_words if (n := _norm(w.text))]
    src = [(n, w) for w in src_words if (n := _norm(w.text))]
    n = len(ref)
    if n < 4 or len(src) < n:
        return None
    ref_str = " ".join(t for t, _ in ref)
    src_tokens = [t for t, _ in src]

    best_score, best_i = 0.0, -1
    for i in range(len(src) - n + 1):
        score = fuzz.ratio(" ".join(src_tokens[i:i + n]), ref_str)
        if score > best_score:
            best_score, best_i = score, i
    if best_score < threshold:
        return None

    # Сдвиг по совпавшим словам (медиана устойчива к ошибкам распознавания)
    window = src[best_i:best_i + n]
    offsets = []
    for (rt, rw) in ref:
        for (st, sw) in window:
            if rt == st and len(rt) > 2:
                offsets.append(sw.start - rw.start)
                break
    if not offsets:
        offsets = [window[0][1].start - ref[0][1].start]
    deltas = sorted(offsets)
    m = median(deltas)
    good = [d for d in deltas if abs(d - m) < 2.0] or deltas
    return best_score, median(good)
