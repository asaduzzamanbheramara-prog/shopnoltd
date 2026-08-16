#!/bin/bash
set -e

# Virtual display for non-headless Chromium so sessions are actually viewable
Xvfb :99 -screen 0 1360x900x24 &
sleep 1

# VNC server pointed at the virtual display, no password for local/internal use
# (put this behind Keycloak/ingress auth before exposing externally — see README)
x11vnc -display :99 -forever -shared -nopw -rfbport 5900 -quiet &
sleep 1

# noVNC web bridge so the browser session can be viewed from a browser tab
websockify --web=/usr/share/novnc 6080 localhost:5900 &

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
