#!/bin/bash
# deploy.sh — rsync project files from local machine to Pi
#
# Usage: PI_HOST=einkdisplay ./deploy.sh
#
# Defaults assume SSH alias "einkdisplay" is configured in ~/.ssh/config
# with the correct User set.

PI_HOST="${PI_HOST:-einkdisplay}"

rsync -avz \
  --exclude='.git' \
  --exclude='.worktrees' \
  --exclude='.superpowers' \
  --exclude='docs/' \
  --exclude='.claude' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='token.json' \
  --exclude='credentials.json' \
  --exclude='config.json' \
  ./ "${PI_HOST}:~/einkdisplay/"

# Install service files with the <user> placeholder substituted to the real user
PI_USER="$(ssh "${PI_HOST}" 'echo $USER')"
for svc in einkdisplay.service einkdisplay-web.service; do
  ssh "${PI_HOST}" "sed 's|<user>|${PI_USER}|g' ~/einkdisplay/${svc} | sudo tee /etc/systemd/system/${svc} > /dev/null"
done
ssh "${PI_HOST}" "sudo systemctl daemon-reload"

echo "Deploy complete. Restart the service if needed:"
echo "  ssh ${PI_HOST} 'sudo systemctl restart einkdisplay einkdisplay-web'"
