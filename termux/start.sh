#!/data/data/com.termux/files/usr/bin/bash
# Convenience wrapper: start olliEcode and open the localhost web UI.
cd "$(dirname "$0")" || exit 1
exec python3 run.py "$@"
