#!/bin/bash
# deploy.sh — stub
# TODO: formalize deploy process (see spec Backlog: Deployment Formalization)
#
# Intended workflow:
#   1. rsync project files from Mac to Pi
#   2. systemd service handles boot/restart
#
# Example rsync (adjust PI_HOST and PI_PATH):
#   PI_HOST="pi@raspberrypi.local"
#   PI_PATH="/home/pi/einkdisplay"
#   rsync -avz --exclude='.git' --exclude='.worktrees' --exclude='__pycache__' \
#     ./ "$PI_HOST:$PI_PATH/"

echo "deploy.sh is a stub — see Backlog in docs/superpowers/specs/2026-03-28-architecture-redesign.md"
exit 1
