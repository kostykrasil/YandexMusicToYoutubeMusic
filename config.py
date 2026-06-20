import sys
from pathlib import Path

# ══════════════════════════════════════════════════════
#  ПРОКСИ ДЛЯ ЯНДЕКС.МУЗЫКИ
# ══════════════════════════════════════════════════════
# Прокси применяется ТОЛЬКО к запросам в Яндекс.Музыку — на YouTube
# Music он не влияет, запросы к YouTube всегда идут напрямую.
# Нужен прокси с РОССИЙСКИМ IP, если, находясь за границей, вы
# получаете от Яндекс.Музыки урезанный каталог/ошибки доступа.
# Поддерживаются http:// и socks5:// (для socks5 один раз поставьте:
# pip install "requests[socks]" --break-system-packages)
USE_YM_PROXY = False
YM_PROXY_URL = ""

APP_DIR = Path.home() / ".playlist_transfer"
APP_DIR.mkdir(parents=True, exist_ok=True)

YM_TOKEN_FILE = APP_DIR / "ym_token.json"
YTM_AUTH_FILE = str(APP_DIR / "ytm_auth.json")

YM_FALLBACK_CLIENT_ID = "23cabbbdc6cd418abb4b39c32c41195d"
YM_FALLBACK_URL = (
    "https://oauth.yandex.ru/authorize"
    f"?response_type=token&client_id={YM_FALLBACK_CLIENT_ID}"
)

YTM_MUSIC_URL = "https://music.youtube.com"
YTM_HELP_URL = "https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html"

LIKED_KIND = 3

C = {
    "bg": "#0d1117",
    "surface": "#161b22",
    "card": "#21262d",
    "border": "#30363d",
    "text": "#e6edf3",
    "dim": "#7d8590",
    "green": "#3fb950",
    "red": "#f85149",
    "blue": "#58a6ff",
    "ym": "#ffdb4d",
    "ytm": "#ff0033",
}

IS_WIN = sys.platform == "win32"
FONT = ("Segoe UI", 10) if IS_WIN else ("Helvetica", 11)
FONT_MONO = ("Consolas", 9) if IS_WIN else ("Menlo", 10)
FONT_B = (FONT[0], FONT[1], "bold")
FONT_SM = (FONT[0], FONT[1] - 1)
FONT_LG = (FONT[0], FONT[1] + 4, "bold")
FONT_TITLE = (FONT[0], FONT[1] + 6, "bold")