#!/usr/bin/env python3
"""AvciCode for Termux - one-command localhost launcher.

Starts the built AvciCode server on 127.0.0.1, prints a one-click
authenticated URL, and opens it in the browser. Everything runs locally;
the only external process is the optional free-model proxy.

Usage:
    python run.py                # start, open browser
    python run.py --no-open      # start, print URL only
    python run.py --port 4096    # fixed port
    python run.py --no-proxy     # do not start the free-model proxy
    python run.py --directory ~/projects/foo
"""

from __future__ import annotations

import argparse
import base64
import os
import platform
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
BUNDLE = APP_DIR / "app" / "opencode.mjs"

HOME = Path.home()
SHARE = HOME / ".local" / "share" / "olliecode"
NODE_DIR = SHARE / "node"
NODE_BIN = NODE_DIR / "bin" / "node"
DATA_DIR = SHARE / "data"
PASSWORD_FILE = SHARE / "web-password"
LOG_FILE = SHARE / "server.log"

NODE_VERSION = "26.4.0"
PROXY_HEALTH = "http://127.0.0.1:8080/healthz"

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
LISTEN = re.compile(r"server listening on (https?://\S+)")

C_RESET = "\033[0m"
C_DIM = "\033[2m"
C_BOLD = "\033[1m"
C_CYAN = "\033[36m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_RED = "\033[31m"


def log(msg: str) -> None:
    print(msg, flush=True)


def die(msg: str, code: int = 1) -> "None":
    print(f"{C_RED}{msg}{C_RESET}", file=sys.stderr, flush=True)
    raise SystemExit(code)


def node_arch() -> str:
    machine = platform.machine().lower()
    if machine in ("aarch64", "arm64"):
        return "arm64"
    if machine in ("x86_64", "amd64"):
        return "x64"
    die(f"Unsupported architecture: {machine} (need aarch64 or x86_64)")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def download(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url, timeout=60) as response:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        with open(dest, "wb") as handle:
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                handle.write(chunk)
                done += len(chunk)
                if total:
                    pct = done * 100 // total
                    sys.stderr.write(f"\r  node runtime {pct:3d}%  {done // 1048576} / {total // 1048576} MiB")
                    sys.stderr.flush()
        sys.stderr.write("\r" + " " * 60 + "\r")
        sys.stderr.flush()


def ensure_node() -> Path:
    if NODE_BIN.is_file() and os.access(NODE_BIN, os.X_OK):
        return NODE_BIN

    if not shutil.which("grun"):
        log(f"{C_YELLOW}[!] glibc-runner not found, installing...{C_RESET}")
        if shutil.which("pkg"):
            subprocess.run(
                ["pkg", "install", "-y", "glibc-runner", "ca-certificates-glibc"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        if not shutil.which("grun"):
            die(
                "grun is missing. Install it first:\n"
                "  pkg install -y glibc-runner ca-certificates-glibc"
            )

    log(f"{C_CYAN}[*] Downloading Node v{NODE_VERSION} (glibc, {node_arch()})...{C_RESET}")
    ensure_dir(SHARE)
    arch = node_arch()
    name = f"node-v{NODE_VERSION}-linux-{arch}"
    url = f"https://nodejs.org/dist/v{NODE_VERSION}/{name}.tar.xz"
    tarball = SHARE / f"{name}.tar.xz"
    try:
        download(url, tarball)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        die(f"Could not download the Node runtime: {exc}")

    tmp = SHARE / "node-extract"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    ensure_dir(tmp)
    with tarfile.open(tarball, "r:xz") as archive:
        archive.extractall(tmp)
    extracted = tmp / name
    if not (extracted / "bin" / "node").is_file():
        die("Node archive did not contain bin/node")
    if NODE_DIR.exists():
        shutil.rmtree(NODE_DIR, ignore_errors=True)
    shutil.move(str(extracted), str(NODE_DIR))
    os.chmod(NODE_BIN, 0o755)
    shutil.rmtree(tmp, ignore_errors=True)
    tarball.unlink(missing_ok=True)
    log(f"{C_GREEN}[+] Node runtime ready{C_RESET}")
    return NODE_BIN


def load_password() -> str:
    ensure_dir(SHARE)
    if PASSWORD_FILE.is_file():
        value = PASSWORD_FILE.read_text(encoding="utf-8").strip()
        if value:
            return value
    value = secrets.token_urlsafe(32)
    PASSWORD_FILE.write_text(value + "\n", encoding="utf-8")
    try:
        os.chmod(PASSWORD_FILE, 0o600)
    except OSError:
        pass
    return value


def proxy_healthy() -> bool:
    try:
        with urllib.request.urlopen(PROXY_HEALTH, timeout=2) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def find_proxy() -> str | None:
    return shutil.which("opencode-proxy") or (
        str(HOME / ".local" / "bin" / "opencode-proxy")
        if (HOME / ".local" / "bin" / "opencode-proxy").is_file()
        else None
    )


def restart_proxy() -> None:
    proxy = find_proxy()
    if not proxy:
        log(f"{C_YELLOW}[!] opencode-proxy not found; cannot rotate WARP exits{C_RESET}")
        return
    log(f"{C_CYAN}[*] Restarting proxy for fresh WARP IPs...{C_RESET}")
    subprocess.run([proxy, "stop"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)


def start_proxy() -> None:
    if proxy_healthy():
        log(f"{C_GREEN}[+] Free-model proxy already running on :8080{C_RESET}")
        return
    proxy = find_proxy()
    if not proxy:
        log(f"{C_YELLOW}[!] opencode-proxy not found; starting without the free-model proxy{C_RESET}")
        return
    log(f"{C_CYAN}[*] Starting free-model proxy on :8080...{C_RESET}")
    try:
        subprocess.Popen(
            [proxy, "start"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        log(f"{C_YELLOW}[!] Could not start proxy: {exc}{C_RESET}")
        return
    deadline = time.time() + 45
    while time.time() < deadline:
        if proxy_healthy():
            log(f"{C_GREEN}[+] Proxy ready{C_RESET}")
            return
        time.sleep(1)
    log(f"{C_YELLOW}[!] Proxy did not come up in 45s; continuing anyway{C_RESET}")


def free_port(hostname: str) -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((hostname, 0))
        return str(sock.getsockname()[1])


def open_url(url: str) -> None:
    candidates = [
        ["termux-open-url", url],
        ["xdg-open", url],
        ["am", "start", "-a", "android.intent.action.VIEW", "-d", url],
    ]
    for command in candidates:
        if shutil.which(command[0]):
            try:
                subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except OSError:
                continue
    try:
        import webbrowser

        webbrowser.open(url)
    except Exception:
        pass


def auth_token(password: str) -> str:
    raw = base64.b64encode(f"opencode:{password}".encode("utf-8")).decode("ascii")
    return urllib.parse.quote(raw, safe="")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AvciCode on localhost.")
    parser.add_argument("--port", default="0", help="port to listen on (default: auto)")
    parser.add_argument("--hostname", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    parser.add_argument("--no-open", action="store_true", help="do not open the browser")
    parser.add_argument("--no-proxy", action="store_true", help="do not start the free-model proxy")
    parser.add_argument("--restart-proxy", action="store_true", help="restart the proxy for fresh WARP IPs")
    parser.add_argument("--no-watch", action="store_true", help="do not auto-rotate WARP when exits are exhausted")
    parser.add_argument("--pure", action="store_true", help="run without external plugins")
    parser.add_argument("--password", default=None, help="server password (default: saved password)")
    parser.add_argument("--directory", default=None, help="working directory / project root")
    args = parser.parse_args()

    if not BUNDLE.is_file():
        die(f"Build not found: {BUNDLE}\nRe-run setup or copy the built app into {APP_DIR / 'app'}")

    ensure_dir(SHARE)
    ensure_dir(DATA_DIR)
    node = ensure_node()
    grun = shutil.which("grun") or "grun"
    password = args.password or load_password()

    if args.directory:
        target = Path(args.directory).expanduser().resolve()
        if not target.is_dir():
            die(f"Not a directory: {target}")
        os.chdir(target)

    watch_proc = None
    if not args.no_proxy:
        if args.restart_proxy:
            restart_proxy()
        start_proxy()
        watch_script = APP_DIR / "warp-watch.py"
        if not args.no_watch and watch_script.is_file() and find_proxy():
            try:
                watch_proc = subprocess.Popen(
                    [sys.executable, str(watch_script)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                log(f"{C_DIM}[*] WARP watch active (auto-rotates on 429 exhaustion){C_RESET}")
            except OSError:
                watch_proc = None

    port = args.port if str(args.port) not in ("0", "", "None") else free_port(args.hostname)

    prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
    env = os.environ.copy()
    env.update(
        {
            "XDG_DATA_HOME": str(DATA_DIR),
            "OPENCODE_PASSWORD": password,
            "OPENCODE_DISABLE_AUTOUPDATE": "true",
            "SSL_CERT_FILE": f"{prefix}/etc/tls/cert.pem",
            "SSL_CERT_DIR": f"{prefix}/etc/ssl/certs",
        }
    )

    command = [
        grun,
        str(node),
        "--experimental-ffi",
        "--use-system-ca",
        "--disable-warning=ExperimentalWarning",
        str(BUNDLE),
    ]
    if args.pure:
        command.append("--pure")
    command += ["serve", "--port", str(port), "--hostname", args.hostname]

    log(f"{C_BOLD}{C_CYAN}AvciCode :: starting server{C_RESET}")
    ensure_dir(LOG_FILE.parent)
    log_file = open(LOG_FILE, "w", encoding="utf-8", errors="replace")

    try:
        process = subprocess.Popen(
            command,
            cwd=str(Path.cwd()),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
    except OSError as exc:
        log_file.close()
        die(f"Could not start the server: {exc}")

    announced = threading.Event()

    def pump() -> None:
        assert process.stdout is not None
        for raw_line in process.stdout:
            line = ANSI.sub("", raw_line).rstrip("\n")
            log(f"{C_DIM}  {line}{C_RESET}")
            log_file.write(raw_line)
            log_file.flush()
            match = LISTEN.search(line)
            if match and not announced.is_set():
                announced.set()
                base_url = match.group(1)
                token = auth_token(password)
                open_target = f"{base_url}/?auth_token={token}"
                log("")
                log(f"{C_GREEN}{C_BOLD}  AvciCode is up{C_RESET}")
                log(f"  {C_BOLD}open{C_RESET}     {open_target}")
                log(f"  {C_BOLD}server{C_RESET}   {base_url}")
                log(f"  {C_BOLD}password{C_RESET} {password}")
                log(f"  {C_DIM}log      {LOG_FILE}{C_RESET}")
                log(f"  {C_DIM}stop     Ctrl-C{C_RESET}")
                log("")
                if not args.no_open:
                    open_url(open_target)

    reader = threading.Thread(target=pump, name="olliecode-log", daemon=True)
    reader.start()

    def interrupt(signum: int, frame: object) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, interrupt)
    signal.signal(signal.SIGTERM, interrupt)

    try:
        while process.poll() is None:
            time.sleep(0.4)
    except KeyboardInterrupt:
        pass
    finally:
        if watch_proc is not None and watch_proc.poll() is None:
            try:
                os.killpg(os.getpgid(watch_proc.pid), signal.SIGTERM)
                watch_proc.wait(timeout=5)
            except (ProcessLookupError, PermissionError, subprocess.TimeoutExpired):
                try:
                    os.killpg(os.getpgid(watch_proc.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
        try:
            if process.poll() is None:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        log_file.close()
        log(f"{C_DIM}server stopped{C_RESET}")


if __name__ == "__main__":
    main()
