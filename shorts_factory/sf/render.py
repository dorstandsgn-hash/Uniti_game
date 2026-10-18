"""Сборка вертикального ролика: размытый фон + чёткое видео + субтитры."""
import json
import subprocess
from pathlib import Path
from statistics import median

W, H = 1080, 1920


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height:format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    st = data["streams"][0]
    return int(st["width"]), int(st["height"]), float(data["format"]["duration"])


def face_center_x(path, samples=24):
    """Где по горизонтали находятся лица (0..1), чтобы не обрезать героев."""
    try:
        import cv2
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    except (ImportError, AttributeError):
        return 0.5

    cap = cv2.VideoCapture(str(path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    centers = []
    for k in range(samples):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * (k + 0.5) / samples))
        ok, frame = cap.read()
        if not ok:
            continue
        fw = frame.shape[1]
        gray = cv2.cvtColor(cv2.resize(frame, None, fx=0.5, fy=0.5), cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, 1.1, 6, minSize=(30, 30))
        if len(faces):
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            centers.append((x + w / 2) * 2 / fw)
    cap.release()
    return median(centers) if centers else 0.5


def _filter(cfg, src_w, src_h, cx):
    fg_h = int(H * cfg.video_height_ratio) // 2 * 2
    scaled_w = src_w * fg_h / src_h
    if scaled_w >= W:
        x = min(max(cx * scaled_w - W / 2, 0), scaled_w - W)
        fg = f"scale=-2:{fg_h},crop={W}:{fg_h}:{int(x)}:0"
    else:  # видео узкое — вписываем по ширине без обрезки
        fg = f"scale={W}:-2"
    b = int(cfg.blur_strength)
    dark = float(cfg.background_darken)
    return (
        f"[0:v]setsar=1,split[a][b];"
        f"[a]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,"
        f"boxblur={b // 3 + 2}:2,scale={W}:{H},eq=brightness={-dark}:saturation=1.15[bg];"
        f"[b]{fg}[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,ass=subs.ass,fps=30,format=yuv420p[v]"
    )


def render(src: Path, ass_text: str, out: Path, cfg, duration=None):
    work = src.parent
    (work / "subs.ass").write_text(ass_text, encoding="utf-8")
    src_w, src_h, src_dur = probe(src)
    cx = face_center_x(src)
    duration = min(duration or src_dur, cfg.max_duration)

    audio = ["-af", "loudnorm=I=-14:TP=-1.5:LRA=11"] if cfg.normalize_audio else []
    base = ["ffmpeg", "-y", "-loglevel", "error", "-i", src.name, "-t", f"{duration:.2f}",
            "-filter_complex", _filter(cfg, src_w, src_h, cx),
            "-map", "[v]", "-map", "0:a?", *audio,
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    encoders = [
        ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "20", "-b:v", "0"],
        ["-c:v", "libx264", "-preset", "medium", "-crf", "19"],
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp_out = work / "render.mp4"
    err = ""
    for enc in encoders:
        r = subprocess.run(base + enc + ["-movflags", "+faststart", tmp_out.name],
                           cwd=work, capture_output=True, text=True)
        if r.returncode == 0:
            tmp_out.replace(out)
            return out
        err = r.stderr
    raise RuntimeError(f"ffmpeg: {err[-800:]}")
