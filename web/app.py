import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# Allow HTTP for local OAuth redirect
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

_BASE = Path(__file__).parent.parent
_CONFIG_PATH = _BASE / "config.json"
_ENV_PATH = _BASE / ".env"
_CREDENTIALS_PATH = _BASE / "credentials.json"
_TOKEN_PATH = _BASE / "token.json"
_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

app = Flask(__name__)
app.secret_key = "einkdisplay-web-secret"


# --- Helpers ---

def _load_config() -> dict:
    with open(_CONFIG_PATH) as f:
        return json.load(f)


def _save_config(cfg: dict) -> None:
    with open(_CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=4)


def _load_env() -> dict:
    env = {}
    if _ENV_PATH.exists():
        for line in _ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def _save_env(env: dict) -> None:
    lines = [f"{k}={v}" for k, v in env.items()]
    _ENV_PATH.write_text("\n".join(lines) + "\n")


def _restart_display() -> None:
    subprocess.run(["sudo", "systemctl", "restart", "einkdisplay"], check=True)


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
        # Format: "Sat 2026-03-28 17:24:28 CDT"
        parts = ts_str.split()
        if len(parts) >= 3:
            started = datetime.strptime(f"{parts[1]} {parts[2]}", "%Y-%m-%d %H:%M:%S")
            delta = datetime.now() - started
            h, rem = divmod(int(delta.total_seconds()), 3600)
            m = rem // 60
            return f"{h}h {m}m"
    except Exception:
        pass
    return ts_str


def _recent_logs(lines: int = 50) -> str:
    result = subprocess.run(
        ["journalctl", "-u", "einkdisplay", f"-n{lines}", "--no-pager", "--output=short"],
        capture_output=True, text=True
    )
    return result.stdout.strip()


def _all_calendars() -> list[dict]:
    """Fetch all calendars from Google account. Returns list of {id, name}."""
    if not _TOKEN_PATH.exists():
        return []
    try:
        creds = Credentials.from_authorized_user_file(str(_TOKEN_PATH), _SCOPES)
        service = build("calendar", "v3", credentials=creds)
        items = service.calendarList().list().execute().get("items", [])
        return [{"id": c["id"], "name": c["summary"]} for c in items]
    except Exception:
        return []


def _oauth_connected_email() -> str | None:
    if not _TOKEN_PATH.exists():
        return None
    try:
        creds = Credentials.from_authorized_user_file(str(_TOKEN_PATH), _SCOPES)
        # The token file contains client_id which has the email encoded, but
        # the simplest check is to see if creds are valid/refreshable.
        if creds.valid or (creds.expired and creds.refresh_token):
            # Try to get email from token info
            info = json.loads(_TOKEN_PATH.read_text())
            return info.get("client_id", "").split("-")[0] or "Connected"
    except Exception:
        pass
    return None


# --- Routes ---

@app.route("/")
def index():
    cfg = _load_config()
    env = _load_env()
    status = _service_status()
    uptime = _service_uptime()
    oauth_email = _oauth_connected_email()
    return render_template("index.html",
        cfg=cfg, env=env, status=status, uptime=uptime,
        oauth_connected=oauth_email is not None,
        oauth_email=oauth_email,
    )


@app.route("/calendar", methods=["GET", "POST"])
def calendar():
    cfg = _load_config()
    all_cals = _all_calendars()
    oauth_email = _oauth_connected_email()

    if request.method == "POST":
        selected = request.form.getlist("calendar_ids")
        max_events = int(request.form.get("calendar_max_events", 3))
        cfg["calendar_ids"] = selected
        cfg["calendar_max_events"] = max(1, min(10, max_events))
        _save_config(cfg)
        try:
            _restart_display()
            flash("Calendar settings saved. Display restarting…", "success")
        except Exception as e:
            flash(f"Settings saved but restart failed: {e}", "warning")
        return redirect(url_for("calendar"))

    return render_template("calendar.html",
        cfg=cfg,
        all_calendars=all_cals,
        oauth_email=oauth_email,
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
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
    return redirect(auth_url)


@app.route("/oauth/callback")
def oauth_callback():
    flow = Flow.from_client_secrets_file(
        str(_CREDENTIALS_PATH), scopes=_SCOPES,
        redirect_uri=url_for("oauth_callback", _external=True)
    )
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    _TOKEN_PATH.write_text(creds.to_json())
    flash("Google account authorized successfully.", "success")
    return redirect(url_for("calendar"))


@app.route("/weather", methods=["GET", "POST"])
def weather():
    cfg = _load_config()
    env = _load_env()

    if request.method == "POST":
        cfg["location_name"] = request.form.get("location_name", "").strip()
        cfg["latitude"] = request.form.get("latitude", "").strip()
        cfg["longitude"] = request.form.get("longitude", "").strip()
        cfg["data_refresh_minutes"] = int(request.form.get("data_refresh_minutes", 60))
        api_key = request.form.get("owm_api_key", "").strip()
        if api_key and not all(c == "•" for c in api_key):
            env["OPEN_WEATHER_MAP_API_KEY"] = api_key
        _save_config(cfg)
        _save_env(env)
        try:
            _restart_display()
            flash("Weather settings saved. Display restarting…", "success")
        except Exception as e:
            flash(f"Settings saved but restart failed: {e}", "warning")
        return redirect(url_for("weather"))

    masked_key = ("•" * 8 + env.get("OPEN_WEATHER_MAP_API_KEY", "")[-4:]) if env.get("OPEN_WEATHER_MAP_API_KEY") else ""
    return render_template("weather.html", cfg=cfg, masked_key=masked_key)


@app.route("/display", methods=["GET", "POST"])
def display():
    cfg = _load_config()
    all_pages = ["clock", "weather_current", "weather_forecast", "calendar"]
    page_labels = {
        "clock": "Clock",
        "weather_current": "Weather — Current",
        "weather_forecast": "Weather — Forecast",
        "calendar": "Calendar",
    }

    if request.method == "POST":
        cfg["page_delay_seconds"] = int(request.form.get("page_delay_seconds", 7))
        # Ordered list from hidden inputs, filtered to enabled checkboxes
        ordered = request.form.getlist("page_order")
        enabled = set(request.form.getlist("pages_enabled"))
        cfg["pages"] = [p for p in ordered if p in enabled]
        if not cfg["pages"]:
            cfg["pages"] = ["clock"]
        _save_config(cfg)
        try:
            _restart_display()
            flash("Display settings saved. Display restarting…", "success")
        except Exception as e:
            flash(f"Settings saved but restart failed: {e}", "warning")
        return redirect(url_for("display"))

    return render_template("display.html",
        cfg=cfg, all_pages=all_pages, page_labels=page_labels
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
    except Exception as e:
        flash(f"Restart failed: {e}", "danger")
    return redirect(url_for("system"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
