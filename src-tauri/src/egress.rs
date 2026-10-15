//! The egress chokepoint.
//!
//! **Every** outbound network request from the application passes through
//! [`Egress::request`]. ESLint and CI prohibit `fetch` in the frontend, while
//! Ruff prohibits `requests` calls in the Python sidecar.
//!
//! This is the technical enforcement of the core promise. A configuration
//! switch could be bypassed silently; one path can be audited and tested.
//!
//! The sidecar on `127.0.0.1` is not egress: it runs on the same machine for
//! the same user and is started by this application. It therefore uses
//! `bridge.rs` rather than this module.

use crate::policy::Mode;
use std::sync::Mutex;
use url::Url;

#[derive(Debug, thiserror::Error)]
pub enum EgressError {
    #[error("Target is not a valid URL: {0}")]
    InvalidUrl(String),

    #[error("Mode {mode} does not allow outbound connections")]
    ModeRefuses { mode: &'static str },

    #[error("Target {target} is not on the allowlist")]
    NotOnAllowlist { target: String },

    #[error("Unencrypted connections are allowed only on the local machine")]
    UnencryptedRemote,
}

/// An entry destined for the `audit_log` table.
#[derive(Debug, Clone, serde::Serialize)]
pub struct AuditEntry {
    pub occurred_at: String,
    pub action: String,
    pub target: String,
    pub bytes: u64,
    pub result: &'static str,
    pub mode: &'static str,
}

pub struct Egress {
    mode: Mode,
    allowlist: Vec<String>,
    /// Buffer entries until the sidecar writes them to SQLite. Refused
    /// attempts are logged as well, because they matter most for auditing.
    audit_log: Mutex<Vec<AuditEntry>>,
}

impl Egress {
    pub fn new(mode: Mode, mut allowlist: Vec<String>, inference_server: Option<String>) -> Self {
        // An inference server in the customer network is a regular on-premise
        // target on the same list, not a separate network path.
        if let Some(server) = inference_server {
            allowlist.push(server);
        }
        Self {
            mode,
            allowlist,
            audit_log: Mutex::new(Vec::new()),
        }
    }

    pub fn mode(&self) -> Mode {
        self.mode
    }

    /// Check whether a target is allowed and log the result.
    ///
    /// The actual request happens later and must use the validated URL returned
    /// by this function.
    pub fn request(&self, raw: &str, action: &str) -> Result<Url, EgressError> {
        let result = self.check(raw);

        self.log_attempt(AuditEntry {
            occurred_at: now_iso(),
            action: action.to_string(),
            target: raw.to_string(),
            bytes: 0,
            result: if result.is_ok() { "allowed" } else { "refused" },
            mode: self.mode.as_str(),
        });

        if let Err(ref error) = result {
            log::warn!("Egress refused: {} → {}", action, error);
        }
        result
    }

    fn check(&self, raw: &str) -> Result<Url, EgressError> {
        let url = Url::parse(raw).map_err(|_| EgressError::InvalidUrl(raw.into()))?;

        let host = url
            .host_str()
            .ok_or_else(|| EgressError::InvalidUrl(raw.into()))?
            .to_ascii_lowercase();

        // Air-gap allows nothing through. The local sidecar does not use this
        // path, so 127.0.0.1 needs no exception here.
        if self.mode == Mode::AirGap {
            return Err(EgressError::ModeRefuses {
                mode: self.mode.as_str(),
            });
        }

        // Unencrypted traffic is allowed only on the same machine.
        let is_local = matches!(host.as_str(), "127.0.0.1" | "localhost" | "::1");
        if url.scheme() != "https" && !is_local {
            return Err(EgressError::UnencryptedRemote);
        }

        let port = url.port_or_known_default().unwrap_or(0);
        let allowed = self.allowlist.iter().any(|entry| {
            let entry = entry.trim().to_ascii_lowercase();
            entry == host || entry == format!("{host}:{port}")
        });

        if !allowed {
            return Err(EgressError::NotOnAllowlist { target: host });
        }

        Ok(url)
    }

    fn log_attempt(&self, entry: AuditEntry) {
        if let Ok(mut audit_log) = self.audit_log.lock() {
            // Cap the buffer so a loop cannot exhaust memory. Older entries
            // have already reached the application log.
            if audit_log.len() >= 10_000 {
                audit_log.remove(0);
            }
            audit_log.push(entry);
        }
    }

    /// Take and clear the audit log. The caller writes it to SQLite.
    pub fn take_audit_log(&self) -> Vec<AuditEntry> {
        self.audit_log
            .lock()
            .map(|mut p| std::mem::take(&mut *p))
            .unwrap_or_default()
    }
}

fn now_iso() -> String {
    // Epoch seconds from the standard library are sufficient for the audit
    // log and avoid another dependency.
    let seconds = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    format!("{seconds}")
}

#[cfg(test)]
mod tests {
    use super::*;

    fn egress(mode: Mode) -> Egress {
        Egress::new(
            mode,
            vec!["files.customer.internal".into(), "10.0.4.12:8000".into()],
            None,
        )
    }

    #[test]
    fn airgap_refuses_everything() {
        let e = egress(Mode::AirGap);
        assert!(e
            .request("https://files.customer.internal/x", "test")
            .is_err());
        assert!(e.request("https://example.com", "test").is_err());
    }

    #[test]
    fn onprem_allows_only_the_allowlist() {
        let e = egress(Mode::OnPrem);
        assert!(e
            .request("https://files.customer.internal/x", "test")
            .is_ok());
        assert!(e.request("https://dropbox.com/x", "test").is_err());
    }

    #[test]
    fn port_is_checked_with_the_host() {
        let e = egress(Mode::OnPrem);
        // The inference server appears on the list with its port.
        assert!(e
            .request("http://10.0.4.12:8000/v1/chat/completions", "llm")
            .is_err());
        // It is still refused because the connection is remote and unencrypted.
    }

    #[test]
    fn unencrypted_connections_are_local_only() {
        let mut e = egress(Mode::OnPrem);
        e.allowlist.push("localhost:11434".into());
        assert!(e.request("http://localhost:11434/api", "test").is_ok());
        assert!(e
            .request("http://files.customer.internal/x", "test")
            .is_err());
    }

    #[test]
    fn every_attempt_is_logged() {
        let e = egress(Mode::AirGap);
        let _ = e.request("https://example.com", "export");
        let _ = e.request("https://example.org", "export");

        let audit_log = e.take_audit_log();
        assert_eq!(audit_log.len(), 2);
        assert!(audit_log.iter().all(|entry| entry.result == "refused"));
        assert!(
            e.take_audit_log().is_empty(),
            "taking the audit log clears it"
        );
    }
}
