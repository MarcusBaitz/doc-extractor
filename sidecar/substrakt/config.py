"""Runtime configuration supplied by the Rust shell through the environment."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

VERSION = "0.1.0"

OperatingMode = Literal["airgap", "onprem", "cloud"]

# Reject unusually large inputs before they can exhaust application memory.
MAX_FILE_BYTES = 512 * 1024 * 1024


@dataclass(frozen=True)
class Config:
    token: str
    bind_host: str
    bind_port: int
    mode: OperatingMode
    data_dir: Path
    model_dir: Path
    log_dir: Path
    # Direct development starts are the only case without a parent PID.
    parent_pid: int | None = None
    development: bool = False
    allowed_roots: list[Path] = field(default_factory=list)


def _path_from_environment(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).expanduser() if value else default


def _default_data_directory() -> Path:
    """Return the platform's conventional application-data directory."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "Substrakt"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Substrakt"
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "substrakt"


def load() -> Config:
    """Read configuration from the environment without exposing the token."""
    token = os.environ.get("SUBSTRAKT_TOKEN", "")
    development = os.environ.get("SUBSTRAKT_DEV") == "1"

    if not token and not development:
        raise SystemExit(
            "SUBSTRAKT_TOKEN is missing. Start the sidecar through the Tauri shell, "
            "or set SUBSTRAKT_DEV=1 for development."
        )

    bind = os.environ.get("SUBSTRAKT_BIND", "127.0.0.1:0")
    host, _, port = bind.rpartition(":")
    host = host or "127.0.0.1"

    # A configuration typo must never expose the sidecar to the network.
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise SystemExit(f"Bind address {host!r} is not local and was rejected.")

    mode = os.environ.get("SUBSTRAKT_MODE", "airgap")
    if mode not in ("airgap", "onprem", "cloud"):
        raise SystemExit(f"Unknown operating mode {mode!r}.")

    data_dir = _path_from_environment("SUBSTRAKT_DATA_DIR", _default_data_directory())
    parent = os.environ.get("SUBSTRAKT_PARENT_PID")

    # An empty read-root list is useful only for direct development starts.
    roots = [
        Path(p).expanduser().resolve()
        for p in os.environ.get("SUBSTRAKT_ROOTS", "").split(os.pathsep)
        if p
    ]

    return Config(
        token=token,
        bind_host="127.0.0.1",
        bind_port=int(port or 0),
        mode=mode,  # type: ignore[arg-type]
        data_dir=data_dir,
        model_dir=_path_from_environment("SUBSTRAKT_MODEL_DIR", data_dir / "models"),
        log_dir=_path_from_environment("SUBSTRAKT_LOG_DIR", data_dir / "logs"),
        parent_pid=int(parent) if parent and parent.isdigit() else None,
        development=development,
        allowed_roots=roots,
    )
