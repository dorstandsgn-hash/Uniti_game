"""Распознавание речи (faster-whisper) с пословными таймкодами."""
import json
import os
import site
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Word:
    text: str
    start: float
    end: float


_model = None
_device = None


def _add_cuda_dlls():
    """На Windows подключает DLL cuBLAS/cuDNN из pip-пакетов nvidia-*."""
    if sys.platform != "win32":
        return
    for sp in site.getsitepackages() + [site.getusersitepackages()]:
        nvidia = Path(sp) / "nvidia"
        if not nvidia.is_dir():
            continue
        for bin_dir in nvidia.glob("*/bin"):
            os.add_dll_directory(str(bin_dir))
            os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ["PATH"]


def _load(cfg, device):
    global _model, _device
    from faster_whisper import WhisperModel

    print("   Загружаю модель распознавания речи... (в первый раз она скачивается,\n"
          "   это ~3 ГБ и 5–20 минут — не закрывайте окно)")
    if device == "cuda":
        _add_cuda_dlls()
        _model = WhisperModel(cfg.whisper_model, device="cuda", compute_type="float16")
    else:
        _model = WhisperModel(cfg.whisper_model_cpu, device="cpu", compute_type="int8")
    _device = device
    print(f"   Whisper: {device.upper()}")


def _load_audio(path):
    """Декодирует звук через ffmpeg в 16 кГц моно (без зависимости от PyAV)."""
    import numpy as np

    raw = subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(path),
         "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


def _run(path, language):
    segments, info = _model.transcribe(_load_audio(path), language=language,
                                    word_timestamps=True, vad_filter=True,
                                    beam_size=5)
    words = []
    for seg in segments:
        for w in seg.words or []:
            text = w.word.strip()
            if text:
                words.append(Word(text, float(w.start), float(w.end)))
    return words, info.language


def transcribe(path, cfg, detect=False):
    """Слова с таймкодами. detect=True — язык определяется сам,
    возвращается (words, язык)."""
    language = None if detect else cfg.language
    if _model is None:
        try:
            _load(cfg, "cuda")
        except Exception as e:
            print(f"   ! Видеокарта недоступна для Whisper ({e}), работаю на процессоре")
            _load(cfg, "cpu")
    try:
        words, lang = _run(path, language)
    except Exception as e:
        # Ошибки CUDA (нет cuBLAS/cuDNN) часто всплывают только при первой расшифровке
        if _device != "cuda":
            raise
        print(f"   ! Ошибка CUDA ({e}), переключаюсь на процессор")
        _load(cfg, "cpu")
        words, lang = _run(path, language)
    return (words, lang) if detect else words


def words_from_json3(path):
    """Пословные таймкоды из автосубтитров YouTube (формат json3)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    raw = []
    for ev in data.get("events", []):
        base = ev.get("tStartMs", 0)
        for seg in ev.get("segs") or []:
            for token in (seg.get("utf8") or "").split():
                raw.append((token, (base + seg.get("tOffsetMs", 0)) / 1000))
    words = []
    for i, (token, start) in enumerate(raw):
        end = raw[i + 1][1] if i + 1 < len(raw) else start + 0.4
        words.append(Word(token, start, min(end, start + 1.5)))
    return words
