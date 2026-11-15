#!/usr/bin/env python3
"""AvciCode WARP watcher — fast IP rotation when the free tier rate-limits.

The proxy already rotates a WARP egress on a 429. This watcher covers the
case the engine reports as `warp_429_exhausted` (every active exit cooling)
and the case where the client keeps seeing 429s because the pool is thin.
When that happens it restarts the proxy, which registers a fresh set of WARP
exits (new public IPv6 /64s) and clears the cooldowns.

Tuned for speed:
  * 1s poll by default.
  * A single client 429 triggers a rotation after WARP_WATCH_GRACE (2s).
  * `warp_429_exhausted` triggers immediately (0s grace).
  * Restart gap is short (12s) so a bad pool is replaced quickly, with a
    backoff that grows only if restarts stop helping.

Standalone:
    python3 warp-watch.py
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HOME = Path.home()
PROXY_LOG = HOME / ".opencode-proxy" / "proxy.log"
PROXY_CLI = HOME / ".local" / "bin" / "opencode-proxy"
STATE_DIR = HOME / ".local" / "share" / "olliecode"
WATCH_LOG = STATE_DIR / "warp-watch.log"
HEALTH = "http://127.0.0.1:8080/healthz"


def env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


INTERVAL = env_float("WARP_WATCH_INTERVAL", 1.0)
EXHAUSTED_GRACE = env_float("WARP_WATCH_GRACE", 2.0)
UNHEALTHY_GRACE = env_float("WARP_WATCH_DOWN_GRACE", 8.0)
STARTUP_GRACE = env_float("WARP_WATCH_STARTUP_GRACE", 30.0)
MIN_RESTART_GAP = env_float("WARP_WATCH_MIN_GAP", 12.0)
MAX_RESTART_GAP = env_float("WARP_WATCH_MAX_GAP", 120.0)
RESTART_TIMEOUT = 90

running = True


def now() -> float:
    return time.monotonic()


def write(message: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {message}"
    print(line, flush=True)
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with open(WATCH_LOG, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass


def health() -> dict | None:
    try:
        with urllib.request.urlopen(HEALTH, timeout=3) as response:
            return json.loads(response.read().decode())
    except Exception:
        return None


def restart_proxy(reason: str) -> None:
    write(f"restarting proxy: {reason}")
    try:
        subprocess.run(
            [str(PROXY_CLI), "restart"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=RESTART_TIMEOUT,
        )
        write("proxy restarted; fresh WARP exits requested")
    except (OSError, subprocess.TimeoutExpired) as exc:
        write(f"proxy restart failed: {exc}")


def stop(signum: int, frame: object) -> None:
    global running
    running = False


def main() -> None:
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    if not PROXY_CLI.is_file():
        write(f"proxy cli not found: {PROXY_CLI}")
        return

    offset = 0
    if PROXY_LOG.is_file():
        offset = PROXY_LOG.stat().st_size
    write(f"watch start (log offset {offset}, interval {INTERVAL}s)")

    started = now()
    last_restart = started - MIN_RESTART_GAP
    zero_since: float | None = None
    down_since: float | None = None
    exhausted_hint = 0.0
    client_hint = 0.0
    gap = MIN_RESTART_GAP
    good_since = now()

    while running:
        # Read newly appended proxy log lines.
        try:
            if PROXY_LOG.is_file():
                size = PROXY_LOG.stat().st_size
                if size < offset:
                    offset = 0
                if size > offset:
                    with open(PROXY_LOG, "r", encoding="utf-8", errors="replace") as handle:
                        handle.seek(offset)
                        chunk = handle.read()
                        offset = handle.tell()
                    for line in chunk.splitlines():
                        if "warp_429_exhausted" in line:
                            exhausted_hint = now()
                            write("detected warp_429_exhausted")
                        elif '"status":429' in line and '"outcome":"client_error"' in line:
                            client_hint = now()
                            write("detected client 429")
                        elif '"status":200' in line and '"outcome":"success"' in line:
                            good_since = now()
                            gap = MIN_RESTART_GAP
        except OSError:
            pass

        data = health()
        t = now()
        if data is None:
            if down_since is None:
                down_since = t
                write("health endpoint unreachable")
            if t - down_since >= UNHEALTHY_GRACE and t - last_restart >= gap:
                restart_proxy("health endpoint unreachable")
                last_restart = now()
                down_since = None
                exhausted_hint = 0.0
                client_hint = 0.0
        else:
            down_since = None
            warp = data.get("warp") or {}
            active = int(warp.get("active") or 0)
            standby = int(warp.get("standby") or 0)
            cooling = int(warp.get("cooling") or 0)
            status = str(warp.get("status") or "")
            usable = active + standby

            if usable == 0:
                if zero_since is None:
                    zero_since = t
            else:
                zero_since = None

            may_restart = t - started >= STARTUP_GRACE and t - last_restart >= gap
            if not may_restart:
                pass
            elif zero_since is not None and t - zero_since >= EXHAUSTED_GRACE:
                restart_proxy(
                    f"no usable WARP exit for {int(t - zero_since)}s "
                    f"(active={active} standby={standby} cooling={cooling})"
                )
                last_restart = now()
                zero_since = None
                exhausted_hint = 0.0
                client_hint = 0.0
                # If restarts keep landing on a dead pool, back off slightly.
                if now() - good_since > 60:
                    gap = min(gap * 1.5, MAX_RESTART_GAP)
            elif exhausted_hint and t - exhausted_hint >= 0.0:
                restart_proxy("warp_429_exhausted")
                last_restart = now()
                exhausted_hint = 0.0
                client_hint = 0.0
            elif client_hint and usable <= 2 and t - client_hint >= 1.0:
                restart_proxy(
                    f"client 429 with {usable} usable exit(s) "
                    f"(active={active} standby={standby} cooling={cooling})"
                )
                last_restart = now()
                client_hint = 0.0
            elif cooling > 0 and usable <= 1 and status != "ready":
                restart_proxy(f"pool degraded (status={status} cooling={cooling} usable={usable})")
                last_restart = now()

        time.sleep(INTERVAL)

    write("watch stop")


if __name__ == "__main__":
    main()
