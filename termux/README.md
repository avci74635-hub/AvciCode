# AvciCode for Termux

The AvciCode fork of OpenCode (built from `gitlab.com/123-group5802346/olliecode`,
source version 2.2.5) running on Termux/Android, plus a one-command launcher that
serves the full web UI on localhost.

The repository ships a desktop/Electron target, which does not run on Android.
This build uses the fork's Node bundle target instead and serves the same web
app the desktop client uses, so the whole chat UI, file tree, terminal, agents
and the AvciCode "Auto JB" toggle work in a normal mobile browser.

## Quick start

```bash
cd ~/olliecode-termux
python3 run.py
```

`run.py` will:

1. Check `glibc-runner` and install it with `pkg` if missing.
2. Download the glibc Node runtime on first run (cached in `~/.local/share/olliecode/node`).
3. Start the free-model proxy (`opencode-proxy`) if it is not already up.
4. Start the AvciCode server on a free loopback port.
5. Print and open a one-click URL that authenticates automatically:

```
http://127.0.0.1:<port>/?auth_token=<base64(opencode:password)>
```

Stop it with `Ctrl-C`.

## Options

```
python3 run.py --no-open          # print the URL, do not open a browser
python3 run.py --port 4096        # fixed port instead of auto
python3 run.py --no-proxy         # do not start the free-model proxy
python3 run.py --restart-proxy    # restart proxy for fresh Cloudflare WARP IPs
python3 run.py --no-watch         # disable the WARP auto-rotation watcher
python3 run.py --pure             # run without external plugins
python3 run.py --password <pw>    # override the saved password
python3 run.py --directory ~/proj # start with a project directory
```

`./start.sh` is the same as `python3 run.py`.

## Layout

```
~/olliecode-termux/
  run.py              launcher (Python stdlib only)
  start.sh            shell wrapper
  app/opencode.mjs    built server (Node bundle)
  app/assets/         embedded web UI + native assets
~/.local/share/olliecode/
  node/               glibc Node runtime used to run the bundle
  data/opencode/      isolated database, logs and sessions
  web-password        saved server password (chmod 600)
  server.log          last server output
```

The launcher runs the fork with `XDG_DATA_HOME` isolated, so it does not touch
the database of a normally installed `opencode`. Your providers in
`~/.config/opencode/opencode.jsonc` are shared by both.

## Models

The config at `~/.config/opencode/opencode.jsonc` points at the local free
proxy on `127.0.0.1:8080`. `run.py` starts it when needed; leave it running and
the fork lists the free models (DeepSeek V4.1 Flash, GLM 5.3 Flash, etc.).

To use other providers, edit `~/.config/opencode/opencode.jsonc` or connect a
provider from the web UI. Nothing is bundled with this build.

The web app needs a moment on first load while it reads the provider catalog;
models appear within a few seconds.

## "Free usage limit" / 429 errors

The upstream anonymous tier rate-limits by public IP. The local proxy spreads
requests across a Cloudflare WARP exit pool, and the current engine (`v1.4.7`)
fixes the two cases that surfaced as a limit error:

- session-title requests were being sent with the full tool set and rejected
  with `403 FreeTierError` / `429 FreeUsageLimitError`; they now go without tools
  and fall back to a synthesized title instead of rotating exits;
- WARP 429s now honor `Retry-After`, so one rate-limited exit no longer burns
  through the whole pool.

This build also widens the WARP pool and watches it:

- `warp.pool_size` raised from 6 to 12 (`preload 6`, `active 6`, `standby 6`),
  so there are more distinct public IPv6 `/64` exits to rotate through.
- `retry.max_attempts` 12 and `performance.failure_cooldown_seconds` 8.
- `warp-watch.py` runs alongside the server. It reads the proxy log for
  `warp_429_exhausted` / client-429 lines and polls `/healthz`; when no WARP
  exit has been usable for 15s (or the engine reports the pool exhausted),
  it restarts the proxy to register a fresh WARP set. Restarts are rate-limited
  to one per 90s and the log is written to `~/.local/share/olliecode/warp-watch.log`.

Manual rotation, and the same watcher for the standalone `opencode` launcher:

```bash
python3 run.py --restart-proxy
opencode-proxy restart
python3 ~/olliecode-termux/warp-watch.py   # run standalone
```

Disable the watcher with `python3 run.py --no-watch`.

To update the proxy engine itself:

```bash
bash ~/olliecode-termux/fix-proxy-limit.sh
```

This installs the latest `opencode2api` release (currently `v1.4.7`) and
restarts it. Do not let `opencode update` downgrade it: the upstream installer
still pins `v1.4.6`, so run `fix-proxy-limit.sh` again after any update.

## Android app (APK)

`olliecode.apk` is a WebView shell that opens the local server and starts it in
Termux. Install it from `~/olliecode-termux/olliecode.apk` (also copied to
`/storage/emulated/0/Download/olliecode.apk`).

```bash
# once, so the app may drive Termux
echo 'allow-external-apps=true' >> ~/.termux/termux.properties
termux-reload-settings
```

- Package `com.olliecode.app`, minSdk 24, targetSdk 34.
- The app opens `http://127.0.0.1:4096` with a baked password (`olliecode-app`).
  `serve-app.sh` is the matching launcher: `bash ~/olliecode-termux/serve-app.sh`.
- First launch shows a start screen. Tap **Start in Termux**; the app fires a
  Termux `RUN_COMMAND` to run `serve-app.sh`, then loads the UI when the port is
  up. **Retry** re-polls, **Open Termux** jumps to the terminal if the intent is
  blocked.
- Uploads, external links and the Android back button are wired to the WebView.

If the intent is refused, run `bash ~/olliecode-termux/serve-app.sh` in Termux
once, then tap **Retry**.

## How it was built

The fork assumes desktop Electron and glibc native modules. The build avoids the
Electron target and uses the Node bundle:

1. Run `bun` under `glibc-runner` (`grun`) because Termux is bionic.
2. `bun install --ignore-scripts`.
3. Add the Android native bindings that the bundlers look for:
   `@rolldown/binding-android-arm64`, `lightningcss-android-arm64`,
   `@tailwindcss/oxide-android-arm64`, `@rollup/rollup-android-arm64`.
4. Build the web app: `node packages/app/node_modules/vite/bin/vite.js build`.
5. Pack `packages/app/dist` into the `app-archive` format (brotli quality 6).
6. `OPENCODE_APP_ARCHIVE=<archive> bun run script/build-node.ts --bundle-only --skip-install`.
7. Run the resulting `dist-node/opencode.mjs` with a glibc Node 26 under `grun`.

That is why the launcher invokes `grun <glibc-node> ... opencode.mjs serve`
instead of a Termux Node.

## Troubleshooting

- **`grun` missing**: `pkg install -y glibc-runner ca-certificates-glibc`.
- **No models listed**: make sure the proxy is up:
  `curl http://127.0.0.1:8080/healthz` and `opencode-proxy start`.
- **Port in use**: omit `--port`; the launcher picks a free one.
- **Browser did not open**: copy the printed `open` URL into your browser.
  If you lost the authenticated URL, open `http://127.0.0.1:<port>` and use the
  password printed by the launcher.
- **Reset sessions**: `rm -rf ~/.local/share/olliecode/data`.
- **Rebuild after updating the repo**: repeat the build steps above and copy
  `packages/cli/dist-node/opencode.mjs` and `dist-node/assets` into `app/`.
