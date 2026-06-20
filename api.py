import re
from config import LIKED_KIND

YM_PLAYLIST_URL_RE = re.compile(r"music\.yandex\.[a-z.]+/users/([^/?#\s]+)/playlists/(\d+)")

class LikedTracksPlaylist:
    kind = LIKED_KIND

    def __init__(self, track_count):
        self.title = "Мне нравится"
        self.track_count = track_count

def _load_ym_playlists(client):
    try:
        playlists = list(client.users_playlists_list() or [])
    except Exception:
        playlists = []

    has_liked = any(getattr(p, "kind", None) == LIKED_KIND for p in playlists)
    if not has_liked:
        try:
            likes = client.users_likes_tracks()
            count = len(getattr(likes, "tracks", None) or [])
            if count:
                playlists.insert(0, LikedTracksPlaylist(count))
        except Exception:
            pass

    return playlists