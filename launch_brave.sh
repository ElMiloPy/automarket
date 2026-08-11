#!/usr/bin/env bash
echo "Launching Brave Browser with Remote Debugging (CDP) on port 9222..."
brave-browser --remote-debugging-port=9222 "$@" &
