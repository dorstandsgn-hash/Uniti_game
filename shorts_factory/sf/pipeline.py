"""Главный конвейер: найти → определить фильм → найти сцену → вырезать → оформить."""
import csv
import json
import re
import shutil
import traceback
from datetime import datetime
from pathlib import Path

from . import asr, render, yt
from .config import ROOT
from .identify import find_movie
from .match import find_offset
from .subs import build_ass

HISTORY = ROOT / "data" / "history.json"


def _load_history():
    try:
        return set(json.loads(HISTORY.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def _save_history(ids):
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps(sorted(ids), ensure_ascii=False, indent=1), encoding="utf-8")


def _slug(text, n=40):
    s = re.sub(r"[^\w\s-]", "", text).strip()
    return re.sub(r"\s+", "_", s)[:n] or "clip"


def find_donor_shorts(cfg, seen):
    """Самые просматриваемые Shorts каналов-доноров, которые ещё не делали."""
    found = []
    for handle in cfg.donor_channels:
        try:
            entries = yt.channel_shorts(cfg, handle, cfg.scan_per_channel)
        except Exception as e:
            print(f"   ! {handle}: {e}")
            continue
        good = [e for e in entries
                if (e.get("view_count") or 0) >= cfg.min_views and e["id"] not in seen]
        print(f"   {handle}: {len(entries)} Shorts, подходящих {len(good)}")
        found += [dict(e, donor=handle) for e in good]
    found.sort(key=lambda e: e.get("view_count") or 0, reverse=True)
    return found


def _source_candidates(cfg, movie, ref_id, ref_dur):
    seen, result = {ref_id}, []
    for q in (f"{movie} фильм", f"{movie} сцена", f"{movie} момент", f"{movie} отрывок"):
        try:
            entries = yt.search(cfg, q, 12)
        except Exception as e:
            print(f"   ! поиск '{q}': {e}")
            continue
        for e in entries:
            dur = e.get("duration") or 0
            url = e.get("url") or ""
            if e["id"] in seen or "/shorts/" in url or not (ref_dur + 15 < dur < 4 * 3600):
                continue
            seen.add(e["id"])
            result.append(e)
        if len(result) >= cfg.max_source_candidates:
            break
    return result[:cfg.max_source_candidates]


def _source_words(cfg, cand, work):
    url = f"https://www.youtube.com/watch?v={cand['id']}"
    subs = yt.auto_subs(cfg, url, work / f"src_{cand['id']}")
    if subs:
        words = asr.words_from_json3(subs)
        if len(words) > 20:
            return words, "автосубтитры"
    if (cand.get("duration") or 0) <= cfg.max_whisper_source_minutes * 60:
        audio = yt.download_audio(cfg, url, work / f"src_{cand['id']}")
        return asr.transcribe(audio, cfg), "whisper"
    return [], "пропущено (длинное, без субтитров)"


def make_short(cfg, src_clip, out_dir, name, meta, duration=None):
    """Из горизонтального фрагмента делает готовый Shorts + файл с описанием."""
    print("   Субтитры...")
    words = asr.transcribe(src_clip, cfg)
    ass = build_ass(words, cfg)
    out = out_dir / f"{name}.mp4"
    print("   Монтаж...")
    render.render(src_clip, ass, out, cfg, duration)
    (out_dir / f"{name}.txt").write_text(meta, encoding="utf-8")
    return out


def _metadata(title, movie, donor_url, source_url):
    clean = re.sub(r"#\S+", "", title or "").strip(" |-–—")
    yt_title = f"{clean} | {movie}" if clean else movie
    tags = "#фильм #сериал #кино #моменты #shorts"
    return (f"НАЗВАНИЕ (для YouTube):\n{yt_title[:100]}\n\n"
            f"ОПИСАНИЕ:\nНазвание: {movie}\n\n{tags}\n\n"
            f"---\nНарезка-донор: {donor_url}\nИсточник видео: {source_url}\n")


def process_donor(cfg, donor, work, out_dir, index):
    ref_url = f"https://www.youtube.com/shorts/{donor['id']}"
    print(f"\n[{index}] {donor.get('title', '')[:70]}  ({donor.get('view_count', 0):,} просм.)")
    info = yt.video_info(cfg, ref_url, comments=True)
    ref_dur = float(info.get("duration") or 0)
    if ref_dur and ref_dur < cfg.min_duration:
        print(f"   — короче {cfg.min_duration} сек, пропускаю")
        return None

    movie = find_movie(info)
    if not movie:
        print("   — не удалось определить фильм, пропускаю")
        return None
    print(f"   Фильм: {movie}")

    ref_audio = yt.download_audio(cfg, ref_url, work / "ref")
    ref_words, lang = asr.transcribe(ref_audio, cfg, detect=True)
    if lang != cfg.language:
        print(f"   — озвучка не на нужном языке ({lang}), пропускаю")
        return None
    if len(ref_words) < 6:
        print("   — в нарезке почти нет речи, сцену не найти, пропускаю")
        return None

    match = None
    for cand in _source_candidates(cfg, movie, donor["id"], ref_dur):
        print(f"   Проверяю: {cand.get('title', '')[:60]}")
        try:
            words, how = _source_words(cfg, cand, work)
        except Exception as e:
            print(f"     ! {e}")
            continue
        res = find_offset(ref_words, words, cfg.match_threshold)
        if res:
            score, offset = res
            print(f"     ✓ сцена найдена ({how}, совпадение {score:.0f}%, с {offset:.1f} сек)")
            match = (cand, offset)
            break
        print(f"     — не то ({how})")
    if not match:
        print("   — сцену в горизонтальном видео не нашёл, пропускаю")
        return None

    cand, offset = match
    source_url = f"https://www.youtube.com/watch?v={cand['id']}"
    duration = min(ref_dur or cfg.max_duration, cfg.max_duration)
    start = max(0.0, offset)
    print(f"   Скачиваю фрагмент {start:.0f}–{start + duration:.0f} сек...")
    clip = yt.download_section(cfg, source_url, start, start + duration + 0.5, work / "clip.mp4")

    name = f"{index:02d}_{_slug(movie)}"
    meta = _metadata(info.get("title"), movie, ref_url, source_url)
    out = make_short(cfg, clip, out_dir, name, meta, duration)
    print(f"   ✅ Готово: {out}")
    return {"file": out.name, "movie": movie, "donor": ref_url, "source": source_url,
            "donor_views": donor.get("view_count")}


def run(cfg, count=None, url=None):
    count = count or cfg.count
    out_dir = Path(cfg.output_dir) / datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_dir.mkdir(parents=True, exist_ok=True)
    seen = _load_history()

    if url:
        vid = re.search(r"(?:shorts/|v=|youtu\.be/)([\w-]{11})", url)
        donors = [{"id": vid.group(1) if vid else url, "title": url}]
    else:
        print("🔎 Ищу залетевшие нарезки у каналов-доноров...")
        donors = find_donor_shorts(cfg, seen)
        print(f"   Кандидатов: {len(donors)}")

    results = []
    for donor in donors:
        if len(results) >= count:
            break
        work = Path(cfg.work_dir) / donor["id"]
        work.mkdir(parents=True, exist_ok=True)
        try:
            res = process_donor(cfg, donor, work, out_dir, len(results) + 1)
            if res:
                results.append(res)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            if re.search(r"не бот|not a bot|Sign in to confirm", str(e)):
                print("   ! YouTube просит подтвердить, что вы не бот. Войдите в YouTube в Firefox\n"
                      "     и укажите в config.yaml:  cookies_from_browser: \"firefox\"")
                break
            print(f"   ! Ошибка: {e}")
            traceback.print_exc(limit=2)
        finally:
            seen.add(donor["id"])
            _save_history(seen)
            if not cfg.keep_work_files:
                shutil.rmtree(work, ignore_errors=True)

    if results:
        with open(out_dir / "report.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(results[0]), delimiter=";")
            w.writeheader()
            w.writerows(results)
    print(f"\n🎬 Готово роликов: {len(results)} из {count}. Папка: {out_dir}")
    return results


def run_manual(cfg, file, start, end, movie):
    """Ручной режим: свой файл фильма + таймкоды."""
    out_dir = Path(cfg.output_dir) / datetime.now().strftime("%Y-%m-%d_%H-%M")
    work = Path(cfg.work_dir) / "manual"
    work.mkdir(parents=True, exist_ok=True)
    clip = work / "clip.mp4"
    import subprocess
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(start), "-to", str(end),
                    "-i", str(file), "-c:v", "libx264", "-crf", "16", "-preset", "fast",
                    "-c:a", "aac", "-b:a", "256k", str(clip)], check=True)
    movie = movie or Path(file).stem
    meta = _metadata("", movie, "-", str(file))
    out = make_short(cfg, clip, out_dir, f"{_slug(movie)}_{int(start)}", meta)
    if not cfg.keep_work_files:
        shutil.rmtree(work, ignore_errors=True)
    print(f"✅ Готово: {out}")
