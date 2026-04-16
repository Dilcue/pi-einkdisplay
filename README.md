# Pi E-Ink Display

Raspberry Pi dashboard on an Adafruit 7.5" tricolor e-ink display (800×480, BWR). Shows today's date, current weather, upcoming calendar events, and a 5-day forecast. Includes a Flask web UI for configuration.

---

## Hardware

- Raspberry Pi 4
- Adafruit 7.5" tricolor e-ink display bonnet (UC8179, BWR)

> **Color note:** The UC8179 OTP waveform always runs both black and red passes unconditionally, regardless of image content. All-red-on-white is the only viable rendering mode — mixed black/red or all-black displays produce washed-out output.

---

## Raspberry Pi Setup

1. Flash Raspberry Pi OS (tested on Trixie, kernel 6.12.x)

2. Enable SPI:
   ```bash
   sudo raspi-config nonint do_spi 0
   ```

3. Reboot

---

## System Packages

```bash
sudo apt install -y python3-pil python3-pip
```

---

## Python Packages

```bash
pip3 install --break-system-packages \
  requests python-dotenv python-dateutil \
  google-api-python-client google-auth-oauthlib \
  flask flask-wtf gpiod adafruit-circuitpython-epd
```

---


## Configuration

Copy the example config and fill in your settings:
```bash
cp config.example.json config.json
```

**`config.json`:**
```json
{
    "location_name": "Your City, ST",
    "latitude": "YOUR_LATITUDE",
    "longitude": "YOUR_LONGITUDE",
    "calendar_ids": [],
    "calendar_max_events": 5,
    "data_refresh_minutes": 60
}
```

**`.env`** — secrets:
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

The web UI runs on port 8080 and lets you configure weather, calendar, and Google OAuth from any browser on your local network.

**Sudoers entry** (required for the web UI to restart the display service):
```bash
sudo visudo
# Add:
<user> ALL=(ALL) NOPASSWD: /bin/systemctl restart einkdisplay
```

**Service setup:**
```bash
sudo cp einkdisplay-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable einkdisplay-web
sudo systemctl start einkdisplay-web
```

Access at `http://einkdisplay.local:8080`

---

## Google Calendar (optional)

1. Create a project in Google Cloud Console, enable the Calendar API, and create an OAuth2 web application credential
2. Download `credentials.json` and copy it to `/home/<user>/einkdisplay/credentials.json`
3. Open the web UI → Calendar → Authorize with Google
4. Select which calendars to display

To re-authorize from the command line (e.g. if the token expires):
```bash
python3 auth_setup.py
scp token.json einkdisplay:/home/<user>/einkdisplay/token.json
ssh einkdisplay "sudo systemctl restart einkdisplay"
```

---

## Running Without systemd

```bash
cd /home/<user>/einkdisplay
python3 main.py
```

---

## Local Simulation

Renders a preview PNG without Pi hardware:
```bash
EINK_SIMULATE=1 python3 simulate.py
open /tmp/einkdisplay/dashboard.png
```
