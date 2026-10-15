# Configuration

Substrakt has deliberately few settings. Its defaults are the safe ones; the
only setting that can open a network path is controlled by the machine's
administrator, not by the user.

## Operating mode and machine-wide policy

The operating mode decides which outbound targets `Egress::request` may
release. It is read at start-up from a JSON policy file:

| Platform | Path (first found wins) |
|---|---|
| Linux | `/etc/substrakt/policy.json`, then `/usr/local/etc/substrakt/policy.json` |
| macOS | `/Library/Application Support/Substrakt/policy.json` |
| Windows | `%ProgramData%\Substrakt\policy.json` |

```json
{
  "mode": "onprem",
  "allowlist": ["files.example.internal", "10.0.4.12:8000"],
  "inference_server": "http://10.0.4.12:8000"
}
```

| Key | Values | Meaning |
|---|---|---|
| `mode` | `airgap`, `onprem`, `cloud` | operating mode; missing means `airgap` |
| `allowlist` | list of `host` or `host:port` | permitted targets; only effective in `onprem` and `cloud` |
| `inference_server` | URL | a vLLM server in the customer network; added to the allowlist and counted as on-premise, not cloud |

**No file means Air-gap. A broken file also means Air-gap**, and the error is
logged. A configuration mistake can never make the application more open.

The policy file is the ceiling. A per-user setting may only narrow the mode,
never widen it (`policy::narrow`); that setting is not yet exposed in the
interface.

## Directories

| What | Default | Override |
|---|---|---|
| Application data, SQLite | Linux: `$XDG_DATA_HOME/substrakt` (`~/.local/share/substrakt`); macOS: `~/Library/Application Support/Substrakt`; Windows: `%APPDATA%\Substrakt`. The shell passes the Tauri app data directory. | `SUBSTRAKT_DATA_DIR` |
| Model weights | `<data dir>/models`; in development `models/` in the repository | `SUBSTRAKT_MODEL_DIR` |
| Logs | `<data dir>/logs`, local and rotating | `SUBSTRAKT_LOG_DIR` |

Logs contain file names, hashes and metrics, never document content.

## Read roots

The sidecar opens only files below its read roots. The shell sets them in
`SUBSTRAKT_ROOTS`: the user's home directory and, where present, `/media`,
`/mnt` and `/srv` on Linux or `/Volumes` on macOS. System directories such as
`/etc`, `/tmp` and `/` are never included. Files on other network shares are
rejected; a share list filled from the file dialog is planned for stage 4.

## Environment variables

The shell sets these when it starts the sidecar. They are documented for
development and diagnosis, not as user settings.

| Variable | Set by | Purpose |
|---|---|---|
| `SUBSTRAKT_TOKEN` | shell | random session token; the sidecar refuses to start without it unless `SUBSTRAKT_DEV=1` |
| `SUBSTRAKT_BIND` | shell | `127.0.0.1:0` |
| `SUBSTRAKT_MODE` | shell | the effective operating mode |
| `SUBSTRAKT_DATA_DIR` | shell | application data directory |
| `SUBSTRAKT_ROOTS` | shell | read roots, separated by the platform path separator |
| `SUBSTRAKT_PARENT_PID` | shell | process ID of the shell |
| `SUBSTRAKT_MODEL_DIR` | optional | model directory; also used by `scripts/fetch-models.sh` |
| `SUBSTRAKT_LOG_DIR` | optional | log directory |
| `SUBSTRAKT_DEV` | developer | `1` lets the sidecar run without a token; `tests/sidecar/conftest.py` sets it for tests |
