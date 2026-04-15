#!/bin/bash
# deploy.sh — rsync project files from local machine to Pi
#
# Usage: PI_USER=<user> PI_HOST=einkdisplay ./deploy.sh
#
# Defaults assume SSH alias "einkdisplay" is configured in ~/.ssh/config.

PI_USER="${PI_USER:-pi}"
PI_HOST="${PI_HOST:-einkdisplay}"
PI_PATH="/home/${PI_USER}/einkdisplay"

rsync -avz \
  --exclude='.git' \
  --exclude='.worktrees' \
  --exclude='.superpowers' \
  --exclude='docs/superpowers' \
  --exclude='.claude' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='token.json' \
  --exclude='credentials.json' \
  --exclude='config.json' \
  ./ "${PI_HOST}:${PI_PATH}/"

echo "Deploy complete. Restart the service if needed:"
echo "  ssh ${PI_HOST} 'sudo systemctl restart einkdisplay einkdisplay-web'"
