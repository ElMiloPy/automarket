#!/usr/bin/env bash
set -e

PORT="${1:-9222}"
BRAVE_BIN="/usr/bin/brave-browser"
MAIN_PROFILE_DIR="$HOME/.config/BraveSoftware/Brave-Browser"

if [ ! -f "$BRAVE_BIN" ]; then
    BRAVE_BIN="$(which brave-browser || which brave || true)"
fi

if [ -z "$BRAVE_BIN" ]; then
    echo "Error: Brave browser binary not found."
    exit 1
fi

echo "============================================================"
echo " Brave Remote Debugging (CDP) Status & Launcher            "
echo " Port: $PORT"
echo "============================================================"

# Check if DevTools HTTP server is TRULY active (must return HTTP 200)
HTTP_STATUS="$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/json/version" || echo "000")"

if [ "$HTTP_STATUS" = "200" ]; then
    echo "[OK] Brave CDP port $PORT is ACTIVE and responding with HTTP 200!"
    echo "     You can run orchestrator.py now without restarting Brave."
    exit 0
fi

echo "[!] Notice: DevTools server on port $PORT is NOT active (HTTP status: $HTTP_STATUS)."
echo ""
echo "CHROMIUM TECHNICAL LIMITATION:"
echo "Chromium (Brave) initializes the DevTools server (port $PORT) ONLY at browser startup."
echo "If Brave was opened without '--remote-debugging-port=$PORT', Chromium ignores the flag"
echo "on subsequent launches and returns HTTP 404."
echo ""
echo "SOLUTION:"
echo "To enable CDP while preserving all your logged-in sessions and cookies, Brave must be"
echo "re-launched once with the remote debugging flag enabled."
echo ""
read -p "Would you like to restart Brave with CDP enabled on your main profile now? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Restarting Brave with remote debugging on main profile..."
    pkill -f "/opt/brave.com/brave/brave" || pkill -f "brave" || true
    sleep 2
    exec "$BRAVE_BIN" --remote-debugging-port="$PORT" --remote-allow-origins="*" --user-data-dir="$MAIN_PROFILE_DIR" "$@"
else
    echo "Skipped restart. To enable CDP manually, start Brave with:"
    echo "  brave-browser --remote-debugging-port=$PORT --remote-allow-origins=*"
fi
