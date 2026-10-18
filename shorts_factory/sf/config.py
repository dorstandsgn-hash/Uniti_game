from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


class Config(dict):
    """Словарь с доступом через точку: cfg.count, cfg.subtitles.font."""

    def __getattr__(self, name):
        try:
            value = self[name]
        except KeyError:
            raise AttributeError(f"В config.yaml нет параметра '{name}'") from None
        return Config(value) if isinstance(value, dict) else value


def load_config(path=None) -> Config:
    path = Path(path) if path else ROOT / "config.yaml"
    with open(path, encoding="utf-8") as f:
        cfg = Config(yaml.safe_load(f))
    for key in ("output_dir", "work_dir"):
        p = Path(cfg[key])
        cfg[key] = str(p if p.is_absolute() else ROOT / p)
    if cfg.get("cookies_file"):
        p = Path(cfg["cookies_file"])
        cfg["cookies_file"] = str(p if p.is_absolute() else ROOT / p)
    return cfg
