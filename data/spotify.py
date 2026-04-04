# data/spotify.py
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import requests

_log = logging.getLogger(__name__)

_DEFAULT_TOKEN_PATH = Path(__file__).parent / "spotify_token.json"
_DEFAULT_CREDS_PATH = Path(__file__).parent / "spotify_credentials.json"
_API_BASE = "https://api.spotify.com/v1"


@dataclass(frozen=True)
class SpotifyData:
    playing: bool
    track: str
    artist: str
    album: str
    progress_ms: int
    duration_ms: int


_IDLE = SpotifyData(playing=False, track="", artist="", album="",
                    progress_ms=0, duration_ms=0)


def _load_token(token_path: Path) -> dict | None:
    if not token_path.exists():
        return None
    try:
        return json.loads(token_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _refresh_token_if_needed(token_path: Path, creds_path: Path) -> str | None:
    token = _load_token(token_path)
    if not token:
        return None

    if time.time() < token.get("expires_at", 0) - 60:
        return token["access_token"]

    if not creds_path.exists():
        return token.get("access_token")  # try anyway

    try:
        creds = json.loads(creds_path.read_text())
    except (json.JSONDecodeError, OSError):
        return token.get("access_token")

    resp = requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"],
        },
        auth=(creds["client_id"], creds["client_secret"]),
        timeout=10,
    )
    if resp.status_code != 200:
        _log.warning("Token refresh failed with status %s", resp.status_code)
        return token.get("access_token")

    new_token = resp.json()
    token["access_token"] = new_token["access_token"]
    token["expires_at"] = int(time.time()) + new_token.get("expires_in", 3600)
    if "refresh_token" in new_token:
        token["refresh_token"] = new_token["refresh_token"]
    token_path.write_text(json.dumps(token))
    return token["access_token"]


def fetch(
    token_path: Path = _DEFAULT_TOKEN_PATH,
    creds_path: Path = _DEFAULT_CREDS_PATH,
) -> SpotifyData:
    access_token = _refresh_token_if_needed(token_path, creds_path)
    if not access_token:
        return _IDLE

    resp = requests.get(
        f"{_API_BASE}/me/player/currently-playing",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if resp.status_code == 204:
        return _IDLE
    if resp.status_code != 200:
        return _IDLE

    data = resp.json()
    item = data.get("item") or {}
    artists = item.get("artists") or [{}]
    return SpotifyData(
        playing=data.get("is_playing", False),
        track=item.get("name", ""),
        artist=artists[0].get("name", "") if artists else "",
        album=(item.get("album") or {}).get("name", ""),
        progress_ms=data.get("progress_ms", 0),
        duration_ms=item.get("duration_ms", 0),
    )
