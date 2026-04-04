# tests/test_spotify.py
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from data.spotify import SpotifyData, fetch, _refresh_token_if_needed


PLAYING_RESPONSE = {
    "is_playing": True,
    "item": {
        "name": "Bohemian Rhapsody",
        "artists": [{"name": "Queen"}],
        "album": {"name": "A Night at the Opera"},
        "duration_ms": 355000,
    },
    "progress_ms": 134000,
}

TOKEN_DATA = {
    "access_token": "test_access",
    "refresh_token": "test_refresh",
    "expires_at": 9999999999,  # far future
    "token_type": "Bearer",
}


def test_fetch_returns_playing_data(tmp_path):
    token_path = tmp_path / "spotify_token.json"
    token_path.write_text(json.dumps(TOKEN_DATA))

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = PLAYING_RESPONSE

    with patch("requests.get", return_value=mock_resp):
        result = fetch(token_path)

    assert result.playing is True
    assert result.track == "Bohemian Rhapsody"
    assert result.artist == "Queen"
    assert result.album == "A Night at the Opera"
    assert result.progress_ms == 134000
    assert result.duration_ms == 355000


def test_fetch_returns_idle_when_204(tmp_path):
    token_path = tmp_path / "spotify_token.json"
    token_path.write_text(json.dumps(TOKEN_DATA))

    mock_resp = MagicMock()
    mock_resp.status_code = 204

    with patch("requests.get", return_value=mock_resp):
        result = fetch(token_path)

    assert result.playing is False
    assert result.track == ""


def test_fetch_returns_idle_when_no_token(tmp_path):
    token_path = tmp_path / "nonexistent_token.json"
    result = fetch(token_path)
    assert result.playing is False


def test_token_refresh_called_when_expired(tmp_path):
    expired_token = {**TOKEN_DATA, "expires_at": 0}  # already expired
    token_path = tmp_path / "spotify_token.json"
    token_path.write_text(json.dumps(expired_token))
    creds_path = tmp_path / "spotify_credentials.json"
    creds_path.write_text(json.dumps({"client_id": "cid", "client_secret": "csec"}))

    refresh_resp = MagicMock()
    refresh_resp.status_code = 200
    refresh_resp.json.return_value = {
        "access_token": "new_token",
        "expires_in": 3600,
        "token_type": "Bearer",
    }
    play_resp = MagicMock()
    play_resp.status_code = 204

    with patch("requests.post", return_value=refresh_resp), \
         patch("requests.get", return_value=play_resp):
        result = fetch(token_path, creds_path=creds_path)

    new_data = json.loads(token_path.read_text())
    assert new_data["access_token"] == "new_token"
