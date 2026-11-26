"""Machine config for every toolkit script: tool paths and render settings.

Reads toolkit/kit.config.json (your machine, not committed). Any key missing there falls back to
kit.config.example.json, and tool paths left empty are looked up on PATH.
Series settings (voices, pauses, interactive choices, title) live in <series root>/series.json, see series_cfg().
"""
import json
import os
import shutil
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent


def _load() -> dict:
    cfg = json.loads((KIT / 'kit.config.example.json').read_text(encoding='utf-8'))
    local = KIT / 'kit.config.json'
    if local.exists():
        cfg.update({k: v for k, v in json.loads(local.read_text(encoding='utf-8')).items() if v not in (None, '')})
    for tool in ('ffmpeg', 'ffprobe'):
        if not cfg.get(tool):
            cfg[tool] = shutil.which(tool) or tool
    if not cfg.get('system_python'):
        cfg['system_python'] = sys.executable
    return {k: os.path.expanduser(v) if isinstance(v, str) and v.startswith('~') else v for k, v in cfg.items()}


P = _load()

SERIES_DEFAULTS = {
    'name': 'SERIES',
    'season': 1,
    'interactive': True,          # each episode ends on an A/B choice (optA/optB marks required)
    'voices': {                   # who -> [kokoro voice, speed]; one locked voice per character for the whole series
        'narrator': ['am_michael', 1.1], 'text': ['am_michael', 1.1],
    },
    'fake_level': 0.3,            # one fixed treatment for every fake_<who> voice
    'pauses': {',': 0.16, ';': 0.22, ':': 0.28, '.': 0.28, '!': 0.28, '?': 0.28, '—': 0.35, '-': 0.35},
    'length_s': [40, 75],
    'caption_top_px': 1480,       # bottom band only
}


def series_cfg(episode_dir) -> dict:
    """series.json next to the episode folders (the series root), merged over SERIES_DEFAULTS."""
    cfg = json.loads(json.dumps(SERIES_DEFAULTS))
    f = Path(episode_dir).resolve().parent / 'series.json'
    if f.exists():
        user = json.loads(f.read_text(encoding='utf-8'))
        voices = {**cfg['voices'], **user.get('voices', {})}
        cfg.update(user)
        cfg['voices'] = voices
    return cfg
