# Pi E-Ink Display

Raspberry Pi Zero W weather and calendar display using a PaPiRus 2.0" e-ink HAT.

---

## Hardware

- Raspberry Pi Zero W
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
  papirus requests python-dotenv python-dateutil \
  google-api-python-client google-auth-oauthlib
```

---

## Deploy Project Files

```bash
rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='.env' \
  /path/to/pi-einkdisplay/ <user>@<pi-ip>:/home/<user>/einkdisplay/
```

---

## Configuration

**`config.json`** — app preferences (committed):
```json
{
    "location_name": "Your City, State",
    "latitude": "0.000000",
    "longitude": "0.000000",
    "calendar_display_name": "Your Calendar Name",
    "page_delay_seconds": 7,
    "data_refresh_minutes": 60
}
```

**`.env`** — secrets (never committed):
```bash
echo "OPEN_WEATHER_MAP_API_KEY=<your_key>" > /home/<user>/einkdisplay/.env
chmod 600 /home/<user>/einkdisplay/.env
```

---

## Google Calendar (optional)

1. Obtain `credentials.json` from Google Cloud Console (Calendar API, OAuth2 desktop app)
2. Run the OAuth flow from a machine with a browser to generate `token.json`
3. Copy both files to `/home/<user>/einkdisplay/`
4. Re-enable calendar in `main.py` by uncommenting the calendar imports, page registration, and refresh call

---

## Running

```bash
cd /home/<user>/einkdisplay
python3 main.py
```

See `docs/superpowers/specs/2026-03-28-architecture-redesign.md` for the full architecture and backlog.
