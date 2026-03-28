# Agentic Setup Instructions

Instructions for an AI agent to replicate this build on a Raspberry Pi 4 (or other modern Pi).

> For Pi Zero W setup see the notes at the bottom — the steps are the same but there are a few differences to be aware of.

---

## Prerequisites (confirm before starting)

- Pi is running Raspberry Pi OS (Bookworm or later, 32-bit or 64-bit)
- SSH is accessible and key auth is configured
- You have the OpenWeatherMap API key
- The project repo is cloned locally at a known path

---

## Step 1 — Verify SSH connectivity

```bash
ssh einkdisplay 'echo connected && uname -a'
```

If this fails, check `~/.ssh/config` for a `Host einkdisplay` entry pointing to the correct IP and key. Confirm the architecture in the output — Pi 4 will show `aarch64` (64-bit) or `armv7l` (32-bit).

---

## Step 2 — Enable SPI, I2C, and the Papirus overlay

```bash
ssh einkdisplay 'sudo raspi-config nonint do_spi 0 && sudo raspi-config nonint do_i2c 0'
ssh einkdisplay 'echo "dtoverlay=papirus,panel=e2200cs021" | sudo tee -a /boot/firmware/config.txt'
ssh einkdisplay 'sudo reboot'
```

Wait for the Pi to come back up (Pi 4 reboots in ~15–20 seconds), then verify:

```bash
ssh einkdisplay 'ls /dev/epd && echo "epd ready"'
```

Expected: `/dev/epd` directory exists. If not, check `dmesg | grep -i papirus` for errors.

**Panel sizes:** Replace `e2200cs021` with the correct value for your screen:
- 1.44" → `e1144cs021`
- 2.0"  → `e2200cs021`
- 2.7"  → `e2271cs021`

---

## Step 3 — Install system packages

```bash
ssh einkdisplay 'sudo apt install -y python3-pil python3-smbus i2c-tools python3-pip'
```

---

## Step 4 — Set up a Python virtual environment

On Pi 4 with Bookworm or later, system Python is externally managed. Use a venv:

```bash
ssh einkdisplay 'python3 -m venv /home/<user>/einkdisplay-venv'
ssh einkdisplay '/home/<user>/einkdisplay-venv/bin/pip install papirus requests python-dotenv python-dateutil google-api-python-client google-auth-oauthlib'
```

Verify:

```bash
ssh einkdisplay '/home/<user>/einkdisplay-venv/bin/python -c "import papirus, PIL, requests, dotenv, dateutil, googleapiclient; print(\"OK\")"'
```

> **Pi Zero W / older OS:** If venv is unavailable, fall back to:
> `pip3 install --break-system-packages <packages>`

---

## Step 5 — Create project directory and deploy files

```bash
ssh einkdisplay 'mkdir -p /home/<user>/einkdisplay'

rsync -avz \
  --exclude='.git' \
  --exclude='.worktrees' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.env' \
  /path/to/pi-einkdisplay/ einkdisplay:/home/<user>/einkdisplay/
```

---

## Step 6 — Write the .env secrets file

```bash
ssh einkdisplay 'echo "OPEN_WEATHER_MAP_API_KEY=<key>" > /home/<user>/einkdisplay/.env && chmod 600 /home/<user>/einkdisplay/.env'
```

---

## Step 7 — Run and verify

```bash
ssh einkdisplay 'cd /home/<user>/einkdisplay && /home/<user>/einkdisplay-venv/bin/python -u main.py 2>&1'
```

Expected: logging output showing weather fetch success, display updating every 7 seconds, e-ink screen cycling through clock, current weather, and forecast pages.

---

## Step 8 — Google Calendar (optional, requires browser on first run)

Calendar is disabled by default in `main.py`. To enable:

1. Obtain `credentials.json` from Google Cloud Console (Calendar API, OAuth2 desktop app)
2. Run the OAuth flow from a machine with a browser — this generates `token.json`
3. Copy both files to the Pi:
   ```bash
   scp credentials.json token.json einkdisplay:/home/<user>/einkdisplay/
   ```
4. In `main.py`, uncomment:
   - `from data import calendar_client`
   - `from pages.calendar_page import CalendarPage`
   - `CalendarPage()` in the pages list
   - `_refresh_calendar(app_data)` calls in `main()`

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `/dev/epd` missing | Overlay not loaded | Verify `dtoverlay=papirus,panel=<size>` in `/boot/firmware/config.txt`, reboot |
| `OSError: cannot open resource` | Fonts not deployed | Ensure `fonts/` was included in rsync |
| `ModuleNotFoundError: papirus` | venv not activated or install failed | Re-run Step 4 with correct venv path |
| `externally-managed-environment` pip error | Bookworm+ system Python protection | Use the venv approach in Step 4 |
| Weather fetch fails | Bad API key or OWM endpoint | Verify `.env` key; OWM `onecall` requires a paid plan as of API v3 |
| Calendar token refresh fails | Expired or missing refresh token | Re-run OAuth flow from a browser machine, copy new `token.json` |

---

## Pi Zero W Notes

The steps above are identical for Pi Zero W with two differences:
- Skip the venv — use `pip3 install --break-system-packages <packages>` instead
- Boot takes 60–90 seconds; wait longer after reboot before retrying SSH
