"""Субтитры в стиле Shorts: по 2–3 слова, жёлтые, с обводкой (формат ASS)."""
import re


def _ass_color(hex_color, alpha=0):
    h = hex_color.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def _ts(t):
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _chunks(words, max_words, max_chars):
    chunk = []
    for i, w in enumerate(words):
        if chunk:
            text_len = len(" ".join(x.text for x in chunk + [w]))
            gap = w.start - chunk[-1].end
            if len(chunk) >= max_words or text_len > max_chars or gap > 0.6:
                yield chunk
                chunk = []
        chunk.append(w)
        if re.search(r"[.!?…]$", w.text):
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def build_ass(words, cfg, width=1080, height=1920):
    s = cfg.subtitles
    style = (
        f"Style: Main,{s.font},{s.size},{_ass_color(s.color)},&H000000FF,"
        f"{_ass_color(s.outline_color)},&H80000000,0,0,0,0,100,100,1,0,1,"
        f"{s.outline},3,5,60,60,0,1"
    )
    wm_style = (f"Style: Mark,Arial,40,{_ass_color('#FFFFFF', 0x90)},&H000000FF,"
                f"&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,1,0,2,40,40,70,1")
    lines = [
        "[Script Info]", "ScriptType: v4.00+",
        f"PlayResX: {width}", f"PlayResY: {height}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        style, wm_style, "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    x, y = width // 2, int(height * s.position_y)
    anim = r"\fscx80\fscy80\t(0,90,\fscx100\fscy100)" if s.pop_animation else ""
    chunks = list(_chunks(words, s.max_words, s.max_chars))
    for i, chunk in enumerate(chunks):
        start = chunk[0].start
        end = chunk[-1].end + 0.15
        if i + 1 < len(chunks):
            end = min(max(end, chunks[i + 1][0].start - 0.05), chunks[i + 1][0].start)
        text = " ".join(w.text for w in chunk).rstrip(",.;:…")
        if s.uppercase:
            text = text.upper()
        text = text.replace("{", "(").replace("}", ")")
        lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Main,,0,0,0,,"
                     f"{{\\pos({x},{y}){anim}}}{text}")
    if cfg.get("watermark"):
        lines.append(f"Dialogue: 1,{_ts(0)},{_ts(3600)},Mark,,0,0,0,,{cfg.watermark}")
    return "\n".join(lines) + "\n"
