//! Start and life cycle of the Python sidecar.
//!
//! Sequence:
//! 1. A 256-bit token is generated and passed through the environment, not as
//!    an argument visible in the process list.
//! 2. The sidecar binds to `127.0.0.1:0`, receives a free port from the kernel
//!    and reports it as one JSON line on stdout.
//! 3. This module reads the line, polls `GET /health` and then marks the
//!    sidecar as connected.
//!
//! The child process's `stdin` stays open. If this application dies, the
//! operating system closes the pipe; the sidecar receives EOF and exits. This
//! is more reliable than checking a PID, because PIDs can be reused.

use rand::RngCore;
use serde::Deserialize;
use std::path::PathBuf;
use std::process::Stdio;
use std::time::Duration;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::{Child, Command};

/// A cold Python start with numpy and scikit-image imports can take several
/// seconds on slower hardware.
const HANDSHAKE_TIMEOUT: Duration = Duration::from_secs(30);
const HEALTH_TIMEOUT: Duration = Duration::from_secs(15);

#[derive(Debug, thiserror::Error)]
pub enum SidecarError {
    #[error("Sidecar could not be started: {0}")]
    Start(String),
    #[error("Handshake failed: {0}")]
    Handshake(String),
    #[error("Sidecar did not respond: {0}")]
    NoResponse(String),
}

#[derive(Debug, Deserialize)]
struct HandshakeLine {
    port: u16,
    #[serde(default)]
    pid: u32,
    #[serde(default)]
    version: String,
    #[serde(default)]
    error: Option<String>,
}

pub struct Sidecar {
    pub port: u16,
    pub token: String,
    pub version: String,
    child: Child,
}

impl Sidecar {
    pub fn basis_url(&self) -> String {
        format!("http://127.0.0.1:{}", self.port)
    }

    /// Shut down cleanly first and forcefully if necessary.
    pub async fn shutdown(mut self, client: &reqwest::Client) {
        let _ = client
            .post(format!("{}/shutdown", self.basis_url()))
            .bearer_auth(&self.token)
            .timeout(Duration::from_secs(3))
            .send()
            .await;

        // Give the process a short time to clean up before terminating it.
        let graceful = tokio::time::timeout(Duration::from_secs(5), self.child.wait()).await;
        if graceful.is_err() {
            log::warn!("Sidecar did not respond to shutdown — terminating it");
            let _ = self.child.kill().await;
        }
    }
}

fn generate_token() -> String {
    let mut bytes = [0u8; 32];
    rand::thread_rng().fill_bytes(&mut bytes);
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

/// Build the start command for the current build mode.
///
/// Development runs the sidecar from the source tree through `uv`, while
/// production uses the bundled binary next to the application.
fn start_command(resources: Option<PathBuf>) -> Command {
    if cfg!(debug_assertions) {
        let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .map(|p| p.join("sidecar"))
            .unwrap_or_else(|| PathBuf::from("sidecar"));

        let mut cmd = Command::new("uv");
        cmd.args(["run", "python", "-m", "substrakt.app"])
            .current_dir(root);
        cmd
    } else {
        let binary = resources
            .unwrap_or_else(|| PathBuf::from("."))
            .join(if cfg!(windows) {
                "substrakt-sidecar.exe"
            } else {
                "substrakt-sidecar"
            });
        Command::new(binary)
    }
}

/// Directories from which the sidecar may read files.
///
/// Without this setting the sidecar cannot enforce its path boundary. The
/// home directory covers the first-stage use case while excluding system
/// files.
///
/// Files on a network drive outside these locations are rejected until the
/// file dialog can populate an explicit allowlist in stage 4.
fn read_roots() -> std::ffi::OsString {
    let mut roots: Vec<PathBuf> = Vec::new();

    if let Some(home) = home_dir() {
        roots.push(home);
    }

    // Linux commonly mounts removable media and network drives here. On
    // Windows, the drive letter in the home path covers the normal case.
    #[cfg(all(unix, not(target_os = "macos")))]
    for path in ["/media", "/mnt", "/srv"] {
        let p = PathBuf::from(path);
        if p.is_dir() {
            roots.push(p);
        }
    }
    #[cfg(target_os = "macos")]
    {
        let p = PathBuf::from("/Volumes");
        if p.is_dir() {
            roots.push(p);
        }
    }

    std::env::join_paths(roots).unwrap_or_default()
}

fn home_dir() -> Option<PathBuf> {
    #[cfg(windows)]
    {
        std::env::var_os("USERPROFILE").map(PathBuf::from)
    }
    #[cfg(not(windows))]
    {
        std::env::var_os("HOME").map(PathBuf::from)
    }
}

pub async fn start(
    resources: Option<PathBuf>,
    data_dir: PathBuf,
    mode: &str,
    client: &reqwest::Client,
) -> Result<Sidecar, SidecarError> {
    let token = generate_token();

    let mut cmd = start_command(resources);
    cmd.env("SUBSTRAKT_TOKEN", &token)
        .env("SUBSTRAKT_BIND", "127.0.0.1:0")
        .env("SUBSTRAKT_MODE", mode)
        .env("SUBSTRAKT_DATA_DIR", &data_dir)
        .env("SUBSTRAKT_ROOTS", read_roots())
        .env("SUBSTRAKT_PARENT_PID", std::process::id().to_string())
        // Models are loaded locally only. These variables prevent a library
        // from downloading missing files unnoticed.
        .env("HF_HUB_OFFLINE", "1")
        .env("TRANSFORMERS_OFFLINE", "1")
        .env("PYTHONUNBUFFERED", "1")
        .stdin(Stdio::piped()) // Keep this open as the watchdog.
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit());

    #[cfg(windows)]
    {
        // Do not open a console window on Windows.
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x0800_0000); // CREATE_NO_WINDOW
    }

    let mut child = cmd
        .kill_on_drop(true)
        .spawn()
        .map_err(|e| SidecarError::Start(e.to_string()))?;

    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| SidecarError::Handshake("stdout is unavailable".into()))?;

    let mut lines = BufReader::new(stdout).lines();

    let line = tokio::time::timeout(HANDSHAKE_TIMEOUT, lines.next_line())
        .await
        .map_err(|_| {
            SidecarError::Handshake(format!(
                "no response within {} seconds",
                HANDSHAKE_TIMEOUT.as_secs()
            ))
        })?
        .map_err(|e| SidecarError::Handshake(e.to_string()))?
        .ok_or_else(|| SidecarError::Handshake("process exited before reporting".into()))?;

    let handshake: HandshakeLine = serde_json::from_str(&line)
        .map_err(|e| SidecarError::Handshake(format!("unreadable message: {e}")))?;

    if let Some(error) = handshake.error {
        return Err(SidecarError::Start(error));
    }

    log::info!(
        "Sidecar started: port {}, PID {}, version {}",
        handshake.port,
        handshake.pid,
        handshake.version
    );

    // Forward remaining sidecar output into the application log. Otherwise a
    // full pipe buffer would eventually block the sidecar.
    tokio::spawn(async move {
        while let Ok(Some(line)) = lines.next_line().await {
            log::debug!("sidecar: {line}");
        }
    });

    let sidecar = Sidecar {
        port: handshake.port,
        token,
        version: handshake.version,
        child,
    };

    wait_for_health(&sidecar, client).await?;
    Ok(sidecar)
}

async fn wait_for_health(sidecar: &Sidecar, client: &reqwest::Client) -> Result<(), SidecarError> {
    let url = format!("{}/health", sidecar.basis_url());
    let deadline = tokio::time::Instant::now() + HEALTH_TIMEOUT;

    loop {
        match client
            .get(&url)
            .timeout(Duration::from_secs(2))
            .send()
            .await
        {
            Ok(response) if response.status().is_success() => return Ok(()),
            _ if tokio::time::Instant::now() >= deadline => {
                return Err(SidecarError::NoResponse(format!(
                    "/health did not respond for {} seconds",
                    HEALTH_TIMEOUT.as_secs()
                )))
            }
            _ => tokio::time::sleep(Duration::from_millis(120)).await,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn token_is_256_bit_hex() {
        let a = generate_token();
        assert_eq!(a.len(), 64, "64 hex characters equal 256 bits");
        assert!(a.chars().all(|c| c.is_ascii_hexdigit()));
        assert_ne!(a, generate_token(), "every start receives a new token");
    }

    #[test]
    fn roots_include_the_home_directory() {
        // An empty root list would disable the sidecar's path boundary. This
        // test secures the values passed along the production start path.
        let roots = read_roots();
        assert!(!roots.is_empty(), "root list must not be empty");

        let home = home_dir().expect("home directory must be available");
        let paths: Vec<PathBuf> = std::env::split_paths(&roots).collect();
        assert!(paths.contains(&home), "the home directory must be readable");

        // System directories must stay outside the read roots.
        for forbidden in ["/etc", "/usr", "/var", "/boot"] {
            assert!(
                !paths.contains(&PathBuf::from(forbidden)),
                "{forbidden} must not be a read root"
            );
        }
    }
}
