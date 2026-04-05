#!/usr/bin/env python3
"""Re-authorize Google Calendar access and write a fresh token.json."""
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
creds = flow.run_local_server(port=0, prompt="select_account")

with open("token.json", "w") as f:
    f.write(creds.to_json())

print("token.json written — copy it to the Pi:")
print("  scp token.json einkdisplay:/home/<user>/einkdisplay/token.json")
print("  ssh einkdisplay 'sudo systemctl restart einkdisplay'")
