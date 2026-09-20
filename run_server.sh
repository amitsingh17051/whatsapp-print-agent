#!/usr/bin/env bash
set -e

pkill -u amitsingh -9 -f "uvicorn app.main:app" || true
pkill -u amitsingh -9 -f "cloudflared" || true
pkill -u amitsingh -9 -f "ngrok" || true
sleep 1

# Start uvicorn with reload in background
/var/www/html/dailyideas/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload &
UVICORN_PID=$!

echo "Uvicorn started with PID $UVICORN_PID"

# Wait for uvicorn to be ready
HEALTHY=0
for i in {1..20}; do
  sleep 1
  if curl -s http://127.0.0.1:8000/health | grep -q "ok"; then
    echo "Uvicorn is healthy!"
    HEALTHY=1
    break
  fi
done

if [ "$HEALTHY" -ne 1 ]; then
  echo "Uvicorn failed to start healthy."
  kill -9 $UVICORN_PID || true
  exit 1
fi

# Trap exit to kill uvicorn when tunnel stops
trap "kill -9 $UVICORN_PID" EXIT

# Start ngrok with permanent domain
echo "Starting ngrok with permanent domain yam-outpour-imperfect.ngrok-free.dev..."
exec /var/www/html/dailyideas/ngrok http 8000 --url https://yam-outpour-imperfect.ngrok-free.dev


