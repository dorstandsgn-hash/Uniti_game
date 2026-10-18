import argparse
import shutil
import sys

from .config import load_config
from .pipeline import run, run_manual


def _seconds(value):
    """'01:12:30' / '72:30' / '4350' -> секунды."""
    total = 0.0
    for part in value.split(":"):
        total = total * 60 + float(part)
    return total


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(prog="shorts_factory", description="Автонарезка Shorts из фильмов")
    p.add_argument("--count", type=int, help="сколько роликов сделать (по умолчанию из config.yaml)")
    p.add_argument("--url", help="сделать ролик по конкретной нарезке-донору (ссылка на Shorts)")
    p.add_argument("--file", help="ручной режим: свой файл фильма")
    p.add_argument("--start", help="ручной режим: начало, например 01:12:30")
    p.add_argument("--end", help="ручной режим: конец, например 01:13:20")
    p.add_argument("--movie", help="ручной режим: название фильма для описания")
    p.add_argument("--config", help="путь к другому config.yaml")
    a = p.parse_args()

    if not shutil.which("ffmpeg"):
        sys.exit("Не найден ffmpeg. Запустите install.bat (или перезапустите окно после установки).")
    cfg = load_config(a.config)
    if a.file:
        if not (a.start and a.end):
            sys.exit("Для --file нужны --start и --end")
        run_manual(cfg, a.file, _seconds(a.start), _seconds(a.end), a.movie)
    else:
        run(cfg, a.count, a.url)
