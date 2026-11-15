#!/data/data/com.termux/files/usr/bin/bash
# Upgrade the local opencode2api proxy to the latest release and restart it.
# v1.4.7+ fixes the FreeTierError / FreeUsageLimitError that appears on
# session-title requests, respects WARP Retry-After, and stops burning the
# whole WARP exit pool on a single 429.
set -euo pipefail

PROXY="$HOME/.local/bin/opencode-proxy"
BIN="$HOME/.opencode-proxy/bin/opencode2api"
API="https://api.github.com/repos/jasonxu114514/opencode2api/releases/latest"

echo "[*] Looking up the latest opencode2api release..."
TAG=$(curl -fsSL --max-time 30 "$API" | python3 -c "import json,sys;print(json.load(sys.stdin)['tag_name'])")
echo "[*] Latest: $TAG"

URL="https://github.com/jasonxu114514/opencode2api/releases/download/${TAG}/opencode2api_${TAG}_linux_arm64.tar.gz"
TMP="${TMPDIR:-$PREFIX/tmp}/opencode2api-upgrade"
rm -rf "$TMP"
mkdir -p "$TMP"

echo "[*] Downloading ${TAG}..."
curl -fsSL --max-time 180 "$URL" -o "$TMP/engine.tar.gz"
if curl -fsSL --max-time 60 "$URL.sha256" -o "$TMP/engine.sha256" 2>/dev/null; then
  EXPECTED=$(awk '{print $1}' "$TMP/engine.sha256")
  ACTUAL=$(sha256sum "$TMP/engine.tar.gz" | awk '{print $1}')
  if [ "$EXPECTED" != "$ACTUAL" ]; then
    echo "[!] sha256 mismatch, aborting"
    exit 1
  fi
  echo "[+] sha256 verified"
fi
tar -xzf "$TMP/engine.tar.gz" -C "$TMP"
NEW=$(find "$TMP" -type f -name opencode2api | head -n 1)
if [ -z "$NEW" ]; then
  echo "[!] Engine binary not found in archive"
  exit 1
fi

echo "[*] Stopping proxy..."
if [ -x "$PROXY" ]; then "$PROXY" stop >/dev/null 2>&1 || true; fi
sleep 2
pkill -9 -f "opencode2api" 2>/dev/null || true
pkill -9 -f "daemon_spawn.py" 2>/dev/null || true
sleep 1

if [ -f "$BIN" ]; then
  cp -f "$BIN" "$BIN.pre-upgrade"
fi
install -m 755 "$NEW" "$BIN"
echo "[+] Installed $TAG"

echo "[*] Starting proxy..."
"$PROXY" start
sleep 8
curl -s --max-time 8 http://127.0.0.1:8080/healthz | python3 -c "
import json,sys
d=json.load(sys.stdin)
print('  version:', d.get('version'))
print('  status :', d.get('status'))
m=d.get('models',{})
print('  models :', m.get('exposed'), '/', m.get('total'))
print('  warp   :', d.get('warp'))
" || echo "[!] Proxy not healthy yet; check: opencode-proxy logs"
