# Pi E-Ink Display

Raspberry Pi weather and calendar display using a PaPiRus 2.0" e-ink HAT. Includes a Flask web UI for configuration accessible from any browser on the local network.

---

## Hardware

- Raspberry Pi 4 (or Zero W)
- PaPiRus 2.0" e-ink HAT (`e2200cs021`)

---

## Raspbian Setup

1. Flash a fresh Raspberry Pi OS (tested on Trixie, kernel 6.12.x)

2. Enable SPI and I2C:
   ```bash
   sudo raspi-config nonint do_spi 0
   sudo raspi-config nonint do_i2c 0
   ```

3. Add the Papirus device tree overlay to `/boot/firmware/config.txt`:
   ```
   dtoverlay=papirus,panel=e2200cs021
   ```

4. Reboot

---

## SSH Access (from Mac)

Add to `~/.ssh/config`:
```
Host einkdisplay
  HostName <pi-ip>
  User <username>
  IdentityFile ~/.ssh/einkdisplay
  IdentitiesOnly yes
```

---

## System Packages

```bash
sudo apt install -y python3-pil python3-smbus i2c-tools python3-pip
```

---

## Python Packages

```bash
pip3 install --break-system-packages \
  requests python-dotenv python-dateutil \
  google-api-python-client google-auth-oauthlib \
  flask flask-wtf gpiod
```

---

## Deploy Project Files

```bash
rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='.env' \
  --exclude='config.json' --exclude='credentials.json' --exclude='token.json' \
  /path/to/pi-einkdisplay/ <user>@<pi-ip>:/home/<user>/einkdisplay/
```

---

## Configuration

Copy the example config and fill in your settings:
```bash
cp config.example.json config.json
```

**`config.json`** — app preferences (not committed, see `config.example.json`):
```json
{
    "location_name": "Your City, ST",
    "latitude": "YOUR_LATITUDE",
    "longitude": "YOUR_LONGITUDE",
    "calendar_display_name": "Your Calendar Name",
    "calendar_ids": [],
    "calendar_max_events": 3,
    "page_delay_seconds": 7,
    "data_refresh_minutes": 60,
    "pages": ["clock", "weather_current", "weather_forecast", "calendar"]
}
```

**`.env`** — secrets (never committed):
```bash
echo "OPEN_WEATHER_MAP_API_KEY=<your_key>" > /home/<user>/einkdisplay/.env
chmod 600 /home/<user>/einkdisplay/.env
```

---

## Display Service (systemd)

```bash
sudo cp einkdisplay.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable einkdisplay
sudo systemctl start einkdisplay
```

---

## Web UI (systemd)

The web UI runs on port 8080 and lets you configure weather, calendar, display pages, and OAuth from any browser on your local network.

**Sudoers entry** (required for the web UI to restart the display service):
```bash
sudo visudo
# Add this line:
<user> ALL=(ALL) NOPASSWD: /bin/systemctl restart einkdisplay
```

**Service setup:**
```bash
sudo cp einkdisplay-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable einkdisplay-web
sudo systemctl start einkdisplay-web
```

Access at: `http://<pi-ip>:8080`

---

## Google Calendar (optional)

1. Obtain `credentials.json` from Google Cloud Console (Calendar API, OAuth2 web app)
2. Copy to `/home/<user>/einkdisplay/credentials.json`
3. Open the web UI → Calendar → Authorize with Google to generate `token.json`
4. Select which calendars to display

---

## Running Without systemd

```bash
cd /home/<user>/einkdisplay
python3 main.py
```

See `docs/superpowers/specs/2026-03-28-architecture-redesign.md` for the full architecture and backlog.
