import json
import sys
import subprocess
from pathlib import Path
from config import USE_YM_PROXY, YM_PROXY_URL

DEPS = {"yandex-music": "yandex_music", "ytmusicapi": "ytmusicapi"}

def _ym_request():
    from yandex_music.utils.request import Request
    if USE_YM_PROXY and YM_PROXY_URL:
        return Request(proxy_url=YM_PROXY_URL)
    return Request()

def _read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return {}

def _write_json(path, data):
    Path(path).write_text(json.dumps(data))

def check_deps():
    missing = []
    for pip_name, mod_name in DEPS.items():
        try:
            __import__(mod_name)
        except ImportError:
            missing.append(pip_name)
    return missing

def install_deps(pkgs, log_fn):
    for pkg in pkgs:
        log_fn(f"  Устанавливаю {pkg}...")
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", pkg],
            capture_output=True, text=True
        )
        if r.returncode != 0:
            log_fn(f"  Ошибка: {r.stderr[:200]}")
            return False
        log_fn(f"  {pkg} установлен")
    return True