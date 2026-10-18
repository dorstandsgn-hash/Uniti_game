"""Всё общение с YouTube через yt-dlp."""
from pathlib import Path

import yt_dlp
from yt_dlp.utils import download_range_func


def _opts(cfg, **extra):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "extractor_args": {"youtube": {"lang": [cfg.language]}},
    }
    if cfg.get("cookies_from_browser"):
        opts["cookiesfrombrowser"] = (cfg.cookies_from_browser,)
    if cfg.get("cookies_file"):
        opts["cookiefile"] = cfg.cookies_file
    opts.update(extra)
    return opts


def _extract(cfg, url, download=False, **extra):
    with yt_dlp.YoutubeDL(_opts(cfg, **extra)) as ydl:
        return ydl.extract_info(url, download=download)


# В списках просмотры пишутся текстом («1,4 млн»); yt-dlp правильно читает
# только английский вариант («1.4M views»), поэтому списки берём на английском.
_EN = {"youtube": {"lang": ["en"]}}


def channel_shorts(cfg, handle, limit):
    """Последние Shorts канала: [{id, title, view_count, url}]."""
    handle = handle if handle.startswith("@") else "@" + handle
    info = _extract(cfg, f"https://www.youtube.com/{handle}/shorts",
                    extract_flat="in_playlist", playlistend=limit, extractor_args=_EN)
    return [e for e in info.get("entries") or [] if e and e.get("id")]


def search(cfg, query, n=10):
    info = _extract(cfg, f"ytsearch{n}:{query}", extract_flat="in_playlist")
    return [e for e in info.get("entries") or [] if e and e.get("id")]


def video_info(cfg, url, comments=False):
    extra = {"skip_download": True}
    if comments:
        extra["getcomments"] = True
        extra["extractor_args"] = {"youtube": {"lang": [cfg.language],
                                               "max_comments": ["40", "40", "0", "0"]}}
    return _extract(cfg, url, **extra)


def download_audio(cfg, url, out_base: Path) -> Path:
    info = _extract(cfg, url, download=True, format="bestaudio/best",
                    outtmpl=str(out_base) + ".%(ext)s")
    return Path(info["requested_downloads"][0]["filepath"])


def auto_subs(cfg, url, out_base: Path):
    """Скачивает автосубтитры (json3). Возвращает путь или None."""
    lang = cfg.language
    try:
        _extract(cfg, url, download=True, skip_download=True,
                 writeautomaticsub=True, writesubtitles=True,
                 subtitleslangs=[lang, f"{lang}-orig"], subtitlesformat="json3",
                 outtmpl=str(out_base) + ".%(ext)s")
    except yt_dlp.utils.DownloadError:
        return None
    found = sorted(out_base.parent.glob(out_base.name + "*.json3"))
    return found[0] if found else None


def download_section(cfg, url, start, end, out_path: Path) -> Path:
    _extract(
        cfg, url, download=True,
        format="bv*[height<=1080][ext=mp4]+ba[ext=m4a]/bv*[height<=1080]+ba/b[height<=1080]/b",
        merge_output_format="mp4",
        download_ranges=download_range_func(None, [(start, end)]),
        force_keyframes_at_cuts=True,
        outtmpl=str(out_path.with_suffix("")) + ".%(ext)s",
    )
    found = sorted(out_path.parent.glob(out_path.stem + ".*"))
    found = [p for p in found if p.suffix in (".mp4", ".mkv", ".webm")]
    if not found:
        raise RuntimeError("не удалось скачать фрагмент")
    return found[0]
