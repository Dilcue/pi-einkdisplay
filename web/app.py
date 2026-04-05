import base64
import json
import logging
import os
import secrets
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests

_log = logging.getLogger(__name__)

import dateutil.parser
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# Allow HTTP for local OAuth redirect (LAN-only deployment)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

_BASE = Path(__file__).parent.parent
_CONFIG_PATH = _BASE / "config.json"
_ENV_PATH = _BASE / ".env"
_CREDENTIALS_PATH = _BASE / "credentials.json"
_TOKEN_PATH = _BASE / "token.json"
_SPOTIFY_TOKEN_PATH = _BASE / "data" / "spotify_token.json"
_SPOTIFY_CREDS_PATH = _BASE / "data" / "spotify_credentials.json"
_SPOTIFY_SCOPES = "user-read-currently-playing user-read-playback-state"
_SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
_SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

_ALL_PAGES = ["clock", "weather", "calendar", "cats", "spotify"]
_PAGE_LABELS = {
    "clock": "Clock",
    "weather": "Weather",
    "calendar": "Calendar",
    "cats": "Cats",
    "spotify": "Spotify",
}


# --- Helpers ---

def _load_env() -> dict:
    env = {}
    if _ENV_PATH.exists():
        for line in _ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")  # strip surrounding quotes
                env[k.strip()] = v
    return env


def _save_env(env: dict) -> None:
    lines = [f"{k}={v}" for k, v in env.items()]
    _ENV_PATH.write_text("\n".join(lines) + "\n")


def _get_or_create_secret_key() -> str:
    env = _load_env()
    if "FLASK_SECRET_KEY" not in env:
        key = secrets.token_hex(32)
        env["FLASK_SECRET_KEY"] = key
        _save_env(env)
        return key
    return env["FLASK_SECRET_KEY"]


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Could not read config.json: {e}") from e


def _save_config(cfg: dict) -> None:
    # Atomic write: write to temp file, then rename to avoid corruption on power loss
    tmp = _CONFIG_PATH.with_suffix(".json.tmp")
    try:
        with open(tmp, "w") as f:
            json.dump(cfg, f, indent=4)
        tmp.rename(_CONFIG_PATH)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _restart_display() -> None:
    result = subprocess.run(
        ["sudo", "systemctl", "restart", "einkdisplay"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "no details"
        _log.error("systemctl restart failed: %s", detail)
        raise RuntimeError("Display restart failed")


def _service_status() -> str:
    result = subprocess.run(
        ["systemctl", "is-active", "einkdisplay"],
        capture_output=True, text=True
    )
    return result.stdout.strip()


def _service_uptime() -> str:
    result = subprocess.run(
        ["systemctl", "show", "einkdisplay", "--property=ActiveEnterTimestamp"],
        capture_output=True, text=True
    )
    line = result.stdout.strip()
    if "=" not in line:
        return "unknown"
    ts_str = line.split("=", 1)[1].strip()
    if not ts_str:
        return "unknown"
    try:
        started = dateutil.parser.parse(ts_str, fuzzy=True)
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        delta = datetime.now(tz=timezone.utc) - started
        h, rem = divmod(int(delta.total_seconds()), 3600)
        m = rem // 60
        return f"{h}h {m}m"
    except Exception:
        return ts_str


def _recent_logs(lines: int = 50) -> str:
    result = subprocess.run(
        ["journalctl", "-u", "einkdisplay", f"-n{lines}", "--no-pager", "--output=short"],
        capture_output=True, text=True
    )
    return result.stdout.strip() or result.stderr.strip() or "(no logs)"


def _all_calendars() -> list[dict]:
    if not _TOKEN_PATH.exists():
        return []
    try:
        creds = Credentials.from_authorized_user_file(str(_TOKEN_PATH), _SCOPES)
        service = build("calendar", "v3", credentials=creds)
        items = service.calendarList().list().execute().get("items", [])
        return [{"id": c["id"], "name": c["summary"]} for c in items]
    except Exception:
        return []


def _spotify_connected() -> str | None:
    """Return display name / 'Connected' if Spotify token exists, else None."""
    if not _SPOTIFY_TOKEN_PATH.exists():
        return None
    try:
        data = json.loads(_SPOTIFY_TOKEN_PATH.read_text())
        return data.get("display_name") or data.get("email") or "Connected"
    except Exception:
        return None


def _oauth_connected_email() -> str | None:
    """Return connected email if token is valid, else None."""
    if not _TOKEN_PATH.exists():
        return None
    try:
        creds = Credentials.from_authorized_user_file(str(_TOKEN_PATH), _SCOPES)
        if not (creds.valid or (creds.expired and creds.refresh_token)):
            return None
        # Try to decode email from id_token JWT payload (no signature check needed here)
        info = json.loads(_TOKEN_PATH.read_text())
        id_token_str = info.get("id_token", "")
        if id_token_str:
            payload = id_token_str.split(".")[1]
            payload += "=" * (-len(payload) % 4)  # pad to multiple of 4
            claims = json.loads(base64.urlsafe_b64decode(payload))
            email = claims.get("email")
            if email:
                return email
        return "Connected"
    except Exception:
        return None


# --- App setup ---

app = Flask(__name__)
app.secret_key = _get_or_create_secret_key()
csrf = CSRFProtect(app)


# --- Routes ---

@app.route("/")
def index():
    try:
        cfg = _load_config()
    except RuntimeError as e:
        return f"<h1>Config error</h1><p>{e}</p>", 500
    status = _service_status()
    uptime = _service_uptime()
    oauth_email = _oauth_connected_email()
    return render_template("index.html",
        cfg=cfg, status=status, uptime=uptime,
        oauth_connected=oauth_email is not None,
        oauth_email=oauth_email,
    )


@app.route("/calendar", methods=["GET", "POST"])
def calendar():
    cfg = _load_config()
    all_cals = _all_calendars()
    oauth_email = _oauth_connected_email()

    if request.method == "POST":
        selected = [c for c in request.form.getlist("calendar_ids") if c]
        try:
            max_events = max(1, min(5, int(request.form.get("calendar_max_events", 3))))
        except ValueError:
            max_events = 3
        cfg["calendar_ids"] = selected
        cfg["calendar_max_events"] = max_events
        _save_config(cfg)
        try:
            _restart_display()
            flash("Calendar settings saved. Display restarting…", "success")
        except RuntimeError:
            flash("Settings saved but display restart failed.", "warning")
        return redirect(url_for("calendar"))

    return render_template("calendar.html",
        cfg=cfg, all_calendars=all_cals, oauth_email=oauth_email,
    )


@app.route("/oauth/start")
def oauth_start():
    if not _CREDENTIALS_PATH.exists():
        flash("credentials.json not found on the server.", "danger")
        return redirect(url_for("calendar"))
    flow = Flow.from_client_secrets_file(
        str(_CREDENTIALS_PATH), scopes=_SCOPES,
        redirect_uri=url_for("oauth_callback", _external=True)
    )
    auth_url, state = flow.authorization_url(prompt="select_account consent", access_type="offline")
    session["oauth_state"] = state
    return redirect(auth_url)


@app.route("/oauth/callback")
def oauth_callback():
    error = request.args.get("error")
    if error:
        flash(f"Google authorization denied: {error}", "danger")
        return redirect(url_for("calendar"))
    expected_state = session.pop("oauth_state", None)
    if not expected_state or request.args.get("state") != expected_state:
        flash("Authorization failed: invalid state. Please try again.", "danger")
        return redirect(url_for("calendar"))
    try:
        flow = Flow.from_client_secrets_file(
            str(_CREDENTIALS_PATH), scopes=_SCOPES,
            redirect_uri=url_for("oauth_callback", _external=True)
        )
        flow.fetch_token(authorization_response=request.url)
        _TOKEN_PATH.write_text(flow.credentials.to_json())
        flash("Google account authorized successfully.", "success")
    except Exception:
        _log.exception("OAuth callback failed")
        flash("Authorization failed. Please try again.", "danger")
    return redirect(url_for("calendar"))


@app.route("/weather", methods=["GET", "POST"])
def weather():
    cfg = _load_config()
    env = _load_env()

    if request.method == "POST":
        lat_str = request.form.get("latitude", "").strip()
        lon_str = request.form.get("longitude", "").strip()
        try:
            lat = float(lat_str)
            lon = float(lon_str)
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                raise ValueError("out of range")
        except ValueError:
            flash("Invalid latitude or longitude. Latitude must be −90..90, longitude −180..180.", "danger")
            return redirect(url_for("weather"))
        cfg["location_name"] = request.form.get("location_name", "").strip()
        cfg["latitude"] = lat_str
        cfg["longitude"] = lon_str
        try:
            cfg["data_refresh_minutes"] = max(5, int(request.form.get("data_refresh_minutes", 60)))
        except ValueError:
            cfg["data_refresh_minutes"] = 60
        api_key = request.form.get("owm_api_key", "").strip()
        if api_key:
            env["OPEN_WEATHER_MAP_API_KEY"] = api_key
        _save_config(cfg)
        _save_env(env)
        try:
            _restart_display()
            flash("Weather settings saved. Display restarting…", "success")
        except RuntimeError:
            flash("Settings saved but display restart failed.", "warning")
        return redirect(url_for("weather"))

    return render_template("weather.html", cfg=cfg,
        has_api_key=bool(env.get("OPEN_WEATHER_MAP_API_KEY")))


@app.route("/display", methods=["GET", "POST"])
def display_settings():
    cfg = _load_config()

    if request.method == "POST":
        try:
            cfg["page_delay_seconds"] = max(2, int(request.form.get("page_delay_seconds", 7)))
        except ValueError:
            cfg["page_delay_seconds"] = 7
        ordered = request.form.getlist("page_order")
        enabled = set(request.form.getlist("pages_enabled"))
        # Validate against known pages to prevent injection into config
        cfg["pages"] = [p for p in ordered if p in enabled and p in _ALL_PAGES]
        if not cfg["pages"]:
            cfg["pages"] = ["clock"]
        _save_config(cfg)
        try:
            _restart_display()
            flash("Display settings saved. Display restarting…", "success")
        except RuntimeError:
            flash("Settings saved but display restart failed.", "warning")
        return redirect(url_for("display_settings"))

    ordered = cfg.get("pages", _ALL_PAGES)
    all_in_order = ordered + [p for p in _ALL_PAGES if p not in ordered]
    return render_template("display.html",
        cfg=cfg, all_pages=_ALL_PAGES, page_labels=_PAGE_LABELS,
        all_in_order=all_in_order,
    )


@app.route("/system")
def system():
    status = _service_status()
    uptime = _service_uptime()
    logs = _recent_logs()
    return render_template("system.html", status=status, uptime=uptime, logs=logs)


@app.route("/system/restart", methods=["POST"])
def system_restart():
    try:
        _restart_display()
        flash("Display service restarted.", "success")
    except RuntimeError:
        flash("Restart failed. Check system logs.", "danger")
    return redirect(url_for("system"))


@app.route("/cats", methods=["GET", "POST"])
def cats_settings():
    cfg = _load_config()

    if request.method == "POST":
        cfg["cats_enabled"] = request.form.get("cats_enabled") == "1"
        try:
            cfg["cat_cache_size"] = max(1, min(20, int(request.form.get("cat_cache_size", 8))))
        except ValueError:
            cfg["cat_cache_size"] = 8
        _save_config(cfg)
        try:
            _restart_display()
            flash("Cats settings saved. Display restarting…", "success")
        except RuntimeError:
            flash("Settings saved but display restart failed.", "warning")
        return redirect(url_for("cats_settings"))

    return render_template("cats.html", cfg=cfg)


@app.route("/spotify", methods=["GET", "POST"])
def spotify():
    cfg = _load_config()
    if request.method == "POST":
        cfg["spotify_enabled"] = "spotify_enabled" in request.form
        _save_config(cfg)
        try:
            _restart_display()
            flash("Spotify settings saved.", "success")
        except RuntimeError:
            flash("Settings saved but display restart failed.", "warning")
        return redirect(url_for("spotify"))
    connected = _spotify_connected()
    return render_template("spotify.html", cfg=cfg, spotify_connected=connected)


@app.route("/spotify/oauth/start")
def spotify_oauth_start():
    if not _SPOTIFY_CREDS_PATH.exists():
        flash("spotify_credentials.json not found on the server.", "danger")
        return redirect(url_for("spotify"))
    creds = json.loads(_SPOTIFY_CREDS_PATH.read_text())
    state = secrets.token_hex(16)
    session["spotify_oauth_state"] = state
    params = {
        "client_id": creds["client_id"],
        "response_type": "code",
        "redirect_uri": url_for("spotify_oauth_callback", _external=True),
        "scope": _SPOTIFY_SCOPES,
        "state": state,
    }
    return redirect(f"{_SPOTIFY_AUTH_URL}?{urlencode(params)}")


@app.route("/spotify/oauth/callback")
def spotify_oauth_callback():
    error = request.args.get("error")
    state_ok = request.args.get("state") == session.pop("spotify_oauth_state", None)
    if error:
        flash(f"Spotify authorization denied: {error}", "danger")
        return redirect(url_for("spotify"))
    if not state_ok:
        flash("Authorization failed: invalid state.", "danger")
        return redirect(url_for("spotify"))
    try:
        creds = json.loads(_SPOTIFY_CREDS_PATH.read_text())
        auth = base64.b64encode(
            f"{creds['client_id']}:{creds['client_secret']}".encode()
        ).decode()
        resp = requests.post(
            _SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": request.args.get("code"),
                "redirect_uri": url_for("spotify_oauth_callback", _external=True),
            },
            headers={"Authorization": f"Basic {auth}"},
            timeout=10,
        )
        resp.raise_for_status()
        token_data = resp.json()
        token_data["expires_at"] = int(time.time()) + token_data.get("expires_in", 3600)
        _tmp = _SPOTIFY_TOKEN_PATH.with_suffix(".json.tmp")
        try:
            _tmp.write_text(json.dumps(token_data))
            _tmp.rename(_SPOTIFY_TOKEN_PATH)
        except Exception:
            _tmp.unlink(missing_ok=True)
            raise
        flash("Spotify account authorized successfully.", "success")
    except Exception:
        _log.exception("Spotify OAuth callback failed")
        flash("Authorization failed. Please try again.", "danger")
    return redirect(url_for("spotify"))


@app.route("/spotify/oauth/revoke", methods=["POST"])
def spotify_oauth_revoke():
    if _SPOTIFY_TOKEN_PATH.exists():
        _SPOTIFY_TOKEN_PATH.unlink()
        flash("Spotify disconnected.", "success")
    return redirect(url_for("spotify"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
