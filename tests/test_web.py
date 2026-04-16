# tests/test_web.py
import json
import os
import pytest


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Create a Flask test app with isolated config/env paths."""
    # Write a minimal config.json for the app to load
    config = {
        "location_name": "Test City",
        "latitude": "40.0",
        "longitude": "-75.0",
        "calendar_ids": [],
        "calendar_max_events": 5,
        "data_refresh_minutes": 60,
        "swap_buttons": False,
        "use_celsius": False,
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))

    env_path = tmp_path / ".env"
    env_path.write_text("FLASK_SECRET_KEY=testsecret\n")

    # Patch module-level paths before importing web.app
    import web.app as webapp
    monkeypatch.setattr(webapp, "_CONFIG_PATH", config_path)
    monkeypatch.setattr(webapp, "_ENV_PATH", env_path)
    monkeypatch.setattr(webapp, "_TOKEN_PATH", tmp_path / "token.json")
    monkeypatch.setattr(webapp, "_CREDENTIALS_PATH", tmp_path / "credentials.json")

    webapp.app.config["TESTING"] = True
    webapp.app.config["WTF_CSRF_ENABLED"] = False
    webapp.app.secret_key = "testsecret"

    return webapp.app


@pytest.fixture
def client(app):
    return app.test_client()


def test_index_returns_200(client, monkeypatch):
    import web.app as webapp
    monkeypatch.setattr(webapp, "_service_status", lambda: "active")
    monkeypatch.setattr(webapp, "_service_uptime", lambda: "2h 30m")
    monkeypatch.setattr(webapp, "_oauth_connected_email", lambda: None)
    resp = client.get("/")
    assert resp.status_code == 200


def test_calendar_get_returns_200(client, monkeypatch):
    import web.app as webapp
    monkeypatch.setattr(webapp, "_all_calendars", lambda: [])
    monkeypatch.setattr(webapp, "_oauth_connected_email", lambda: None)
    resp = client.get("/calendar")
    assert resp.status_code == 200


def test_calendar_post_saves_and_redirects(client, monkeypatch, tmp_path):
    import web.app as webapp
    monkeypatch.setattr(webapp, "_restart_display", lambda: None)
    resp = client.post("/calendar", data={
        "calendar_ids": ["cal1@group.calendar.google.com"],
        "calendar_max_events": "5",
    })
    assert resp.status_code == 302
    # Config should be updated
    cfg = json.loads((tmp_path / "config.json").read_text())
    assert cfg["calendar_ids"] == ["cal1@group.calendar.google.com"]
    assert cfg["calendar_max_events"] == 5


def test_calendar_max_events_clamped(client, monkeypatch, tmp_path):
    import web.app as webapp
    monkeypatch.setattr(webapp, "_restart_display", lambda: None)
    resp = client.post("/calendar", data={
        "calendar_ids": [],
        "calendar_max_events": "999",
    })
    assert resp.status_code == 302
    cfg = json.loads((tmp_path / "config.json").read_text())
    assert cfg["calendar_max_events"] == 5  # clamped from 999


def test_weather_get_returns_200(client, monkeypatch):
    import web.app as webapp
    resp = client.get("/weather")
    assert resp.status_code == 200


def test_weather_post_valid(client, monkeypatch):
    import web.app as webapp
    monkeypatch.setattr(webapp, "_restart_display", lambda: None)
    resp = client.post("/weather", data={
        "location_name": "Philadelphia, PA",
        "latitude": "39.95",
        "longitude": "-75.16",
        "data_refresh_minutes": "30",
        "owm_api_key": "",
    })
    assert resp.status_code == 302


def test_weather_post_invalid_lat(client, monkeypatch, tmp_path):
    import web.app as webapp
    original_lat = json.loads((tmp_path / "config.json").read_text())["latitude"]
    resp = client.post("/weather", data={
        "location_name": "Nowhere",
        "latitude": "999",
        "longitude": "0",
        "data_refresh_minutes": "60",
    })
    assert resp.status_code == 302
    # Config must NOT have been updated with the invalid value
    cfg = json.loads((tmp_path / "config.json").read_text())
    assert cfg["latitude"] == original_lat


def test_system_get_returns_200(client, monkeypatch):
    import web.app as webapp
    monkeypatch.setattr(webapp, "_service_status", lambda: "active")
    monkeypatch.setattr(webapp, "_service_uptime", lambda: "1h 0m")
    monkeypatch.setattr(webapp, "_recent_logs", lambda: "log line 1\nlog line 2")
    resp = client.get("/system")
    assert resp.status_code == 200


def test_system_settings_post_saves_swap_buttons(client, monkeypatch, tmp_path):
    import web.app as webapp
    monkeypatch.setattr(webapp, "_restart_display", lambda: None)
    resp = client.post("/system/settings", data={"swap_buttons": "1"})
    assert resp.status_code == 302
    cfg = json.loads((tmp_path / "config.json").read_text())
    assert cfg["swap_buttons"] is True


def test_system_settings_post_clears_swap_buttons(client, monkeypatch, tmp_path):
    import web.app as webapp
    monkeypatch.setattr(webapp, "_restart_display", lambda: None)
    resp = client.post("/system/settings", data={"swap_buttons": "0"})
    assert resp.status_code == 302
    cfg = json.loads((tmp_path / "config.json").read_text())
    assert cfg["swap_buttons"] is False


def test_weather_post_saves_celsius(client, monkeypatch, tmp_path):
    import web.app as webapp
    monkeypatch.setattr(webapp, "_restart_display", lambda: None)
    resp = client.post("/weather", data={
        "location_name": "Test City",
        "latitude": "40.0",
        "longitude": "-75.0",
        "data_refresh_minutes": "60",
        "owm_api_key": "",
        "use_celsius": "1",
    })
    assert resp.status_code == 302
    cfg = json.loads((tmp_path / "config.json").read_text())
    assert cfg["use_celsius"] is True


def test_system_restart_post(client, monkeypatch):
    import web.app as webapp
    monkeypatch.setattr(webapp, "_restart_display", lambda: None)
    resp = client.post("/system/restart")
    assert resp.status_code == 302


def test_system_restart_post_failure(client, monkeypatch):
    import web.app as webapp
    def _fail(): raise RuntimeError("restart failed")
    monkeypatch.setattr(webapp, "_restart_display", _fail)
    resp = client.post("/system/restart")
    assert resp.status_code == 302


def test_oauth_callback_invalid_state(client):
    resp = client.get("/oauth/callback?state=badstate&code=somecode")
    assert resp.status_code == 302


def test_oauth_callback_error_param(client):
    resp = client.get("/oauth/callback?error=access_denied")
    assert resp.status_code == 302


def test_load_env_parses_quoted_values(tmp_path, monkeypatch):
    import web.app as webapp
    env_path = tmp_path / ".env"
    env_path.write_text('KEY="quoted_value"\nOTHER=plain\n')
    monkeypatch.setattr(webapp, "_ENV_PATH", env_path)
    env = webapp._load_env()
    assert env["KEY"] == "quoted_value"
    assert env["OTHER"] == "plain"


def test_load_env_ignores_comments(tmp_path, monkeypatch):
    import web.app as webapp
    env_path = tmp_path / ".env"
    env_path.write_text("# this is a comment\nKEY=value\n")
    monkeypatch.setattr(webapp, "_ENV_PATH", env_path)
    env = webapp._load_env()
    assert "# this is a comment" not in env
    assert env["KEY"] == "value"


def test_save_config_atomic(tmp_path, monkeypatch):
    import web.app as webapp
    config_path = tmp_path / "config.json"
    config_path.write_text("{}")
    monkeypatch.setattr(webapp, "_CONFIG_PATH", config_path)
    webapp._save_config({"key": "value"})
    assert json.loads(config_path.read_text()) == {"key": "value"}
    assert not (tmp_path / "config.json.tmp").exists()


def test_index_returns_500_on_bad_config(client, monkeypatch):
    import web.app as webapp
    monkeypatch.setattr(webapp, "_load_config", lambda: (_ for _ in ()).throw(RuntimeError("bad config")))
    resp = client.get("/")
    assert resp.status_code == 500
    assert b"Config error" in resp.data


def test_oauth_start_no_credentials(client, monkeypatch, tmp_path):
    import web.app as webapp
    # credentials.json does not exist — should flash danger and redirect
    monkeypatch.setattr(webapp, "_CREDENTIALS_PATH", tmp_path / "missing_credentials.json")
    resp = client.get("/oauth/start")
    assert resp.status_code == 302
    assert "/calendar" in resp.headers["Location"]
