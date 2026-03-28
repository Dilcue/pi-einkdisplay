# Agentic Setup Instructions

Instructions for an AI agent to replicate this build on a Raspberry Pi 4 (or other modern Pi).

> For Pi Zero W setup see the notes at the bottom — the steps are the same but there are a few differences to be aware of.

---

## Prerequisites (confirm before starting)

- Pi is running Raspberry Pi OS (Bookworm or Trixie, 32-bit or 64-bit)
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

Wait for the Pi to come back up (~15–20 seconds), then verify the framebuffer device exists:

```bash
ssh einkdisplay 'ls /dev/fb* && dmesg | grep repaper'
```

Expected: `/dev/fb0` (or `fb1`) and a `Initialized repaper` line in dmesg. The display uses the kernel's DRM repaper driver — there is no `/dev/epd` on kernel 6.x.

**Panel sizes:** Replace `e2200cs021` with the correct value for your screen:
- 1.44" → `e1144cs021`
- 2.0"  → `e2200cs021`
- 2.7"  → `e2271cs021`

---

## Step 3 — Hide the terminal cursor

Prevents the bash cursor from bleeding onto the e-ink display:

```bash
ssh einkdisplay 'sudo sed -i "s/$/ vt.global_cursor_default=0 logo.nologo/" /boot/firmware/cmdline.txt'
```

---

## Step 4 — Install system packages

```bash
ssh einkdisplay 'sudo apt update -qq && sudo apt install -y python3-pil python3-smbus i2c-tools python3-pip'
```

---

## Step 5 — Set up a Python virtual environment

```bash
ssh einkdisplay 'python3 -m venv /home/<user>/einkdisplay-venv'
ssh einkdisplay '/home/<user>/einkdisplay-venv/bin/pip install pillow requests python-dotenv python-dateutil google-api-python-client google-auth-oauthlib'
```

Verify:

```bash
ssh einkdisplay '/home/<user>/einkdisplay-venv/bin/python -c "import PIL, requests, dotenv, dateutil, googleapiclient; print(\"OK\")"'
```

> **Pi Zero W / older OS:** If venv is unavailable, use:
> `pip3 install --break-system-packages pillow requests python-dotenv python-dateutil google-api-python-client google-auth-oauthlib`

---

## Step 6 — Deploy project files

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

## Step 7 — Write the .env secrets file

```bash
ssh einkdisplay 'echo "OPEN_WEATHER_MAP_API_KEY=<key>" > /home/<user>/einkdisplay/.env && chmod 600 /home/<user>/einkdisplay/.env'
```

---

## Step 8 — Set up systemd service

```bash
ssh einkdisplay 'cat > /tmp/einkdisplay.service << '"'"'EOF'"'"'
[Unit]
Description=E-Ink Display
After=network-online.target
Wants=network-online.target

[Service]
User=<user>
WorkingDirectory=/home/<user>/einkdisplay
ExecStart=/home/<user>/einkdisplay-venv/bin/python -u main.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
sudo cp /tmp/einkdisplay.service /etc/systemd/system/einkdisplay.service && sudo systemctl daemon-reload && sudo systemctl enable einkdisplay && sudo systemctl start einkdisplay'
```

Verify it started:

```bash
ssh einkdisplay 'sudo systemctl status einkdisplay --no-pager'
```

---

## Step 9 — Reboot and verify

```bash
ssh einkdisplay 'sudo reboot'
# Wait ~20 seconds, then:
ssh einkdisplay 'sudo systemctl status einkdisplay --no-pager'
```

Expected: `Active: active (running)` and a weather fetch log line. Display should be cycling through pages with no cursor visible.

---

## Step 10 — Google Calendar (optional, requires browser on first run)

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
5. Restart the service:
   ```bash
   ssh einkdisplay 'sudo systemctl restart einkdisplay'
   ```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| No `/dev/fb0` after reboot | Overlay not loaded | Verify `dtoverlay=papirus,panel=<size>` in `/boot/firmware/config.txt`, reboot |
| `OSError: cannot open resource` | Fonts not deployed | Ensure `fonts/` was included in rsync |
| `ModuleNotFoundError` | venv not activated or install failed | Re-run Step 5 with correct venv path |
| `externally-managed-environment` pip error | Bookworm+ system Python protection | Use the venv approach in Step 5 |
| Weather fetch 401 error | OWM onecall requires paid plan | The app uses `/data/2.5/weather` and `/data/2.5/forecast` (free tier) — verify API key |
| Cursor visible on display | cmdline.txt not updated | Re-run Step 3 and reboot |
| Calendar token refresh fails | Expired or missing refresh token | Re-run OAuth flow from a browser machine, copy new `token.json` |
| Service not starting | Check logs | `sudo journalctl -u einkdisplay -n 50` |

---

## Pi Zero W Notes

The steps above are identical for Pi Zero W with two differences:
- Skip the venv — use `pip3 install --break-system-packages <packages>` instead
- Boot takes 60–90 seconds; wait longer after reboot before retrying SSH
