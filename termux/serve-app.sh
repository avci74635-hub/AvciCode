#!/data/data/com.termux/files/usr/bin/bash
# Fixed-config launcher for the AvciCode Android app (olliecode.apk).
# The APK opens http://127.0.0.1:4096 and authenticates with this password.
# Run it once from Termux, or let the app fire it through RUN_COMMAND.
cd "$(dirname "$0")" || exit 1
exec python3 run.py --no-open --port 4096 --password "olliecode-app" "$@"
