//! Operating mode and machine-wide policy.
//!
//! Three modes are kept strictly separate. A machine-wide policy file controls
//! the mode and cannot be overridden by the user, so an IT department can
//! enforce Air-gap. Air-gap applies when the file is absent.
//!
//! The order is deliberate: policy beats user preference, which beats the
//! default. A user preference can only narrow the mode, never widen it.

use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Mode {
    /// Only 127.0.0.1. This is the default.
    AirGap,
    /// Additionally allows administratively managed customer-network targets.
    OnPrem,
    /// Additionally allows external providers after explicit approval.
    Cloud,
}

impl Mode {
    pub fn as_str(self) -> &'static str {
        match self {
            Mode::AirGap => "airgap",
            Mode::OnPrem => "onprem",
            Mode::Cloud => "cloud",
        }
    }

    /// Return mode strictness; a lower value is stricter.
    fn strictness(self) -> u8 {
        match self {
            Mode::AirGap => 0,
            Mode::OnPrem => 1,
            Mode::Cloud => 2,
        }
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Policy {
    #[serde(default)]
    pub mode: Option<Mode>,
    /// Allowed targets as host or host:port. Only effective in onprem/cloud.
    #[serde(default)]
    pub allowlist: Vec<String>,
    /// Address of a vLLM server in the customer network. This counts as an
    /// on-premise target, not a cloud target.
    #[serde(default)]
    pub inference_server: Option<String>,
}

/// Machine-wide policy paths in descending precedence.
fn policy_paths() -> Vec<PathBuf> {
    #[cfg(target_os = "windows")]
    {
        let programdata = std::env::var("ProgramData").unwrap_or_else(|_| r"C:\ProgramData".into());
        vec![PathBuf::from(programdata)
            .join("Substrakt")
            .join("policy.json")]
    }
    #[cfg(target_os = "macos")]
    {
        vec![PathBuf::from(
            "/Library/Application Support/Substrakt/policy.json",
        )]
    }
    #[cfg(all(unix, not(target_os = "macos")))]
    {
        vec![
            PathBuf::from("/etc/substrakt/policy.json"),
            PathBuf::from("/usr/local/etc/substrakt/policy.json"),
        ]
    }
}

/// Load the policy. Air-gap applies when the file is absent or invalid.
///
/// A broken policy file must never put the application into a less restrictive
/// mode. Locality wins when the configuration is uncertain.
pub fn load() -> (Mode, Policy) {
    for path in policy_paths() {
        let Ok(contents) = std::fs::read_to_string(&path) else {
            continue;
        };
        match serde_json::from_str::<Policy>(&contents) {
            Ok(policy) => {
                let mode = policy.mode.unwrap_or(Mode::AirGap);
                log::info!(
                    "Loaded policy from {}: mode {}",
                    path.display(),
                    mode.as_str()
                );
                return (mode, policy);
            }
            Err(err) => {
                log::error!(
                    "Policy {} is invalid ({}) — enforcing Air-gap",
                    path.display(),
                    err
                );
                return (Mode::AirGap, Policy::default());
            }
        }
    }
    (Mode::AirGap, Policy::default())
}

/// Apply a user preference. It may only narrow the mode, never widen it.
pub fn narrow(policy_mode: Mode, preference: Mode) -> Mode {
    if preference.strictness() <= policy_mode.strictness() {
        preference
    } else {
        log::warn!(
            "Policy limits mode {} to {}",
            preference.as_str(),
            policy_mode.as_str()
        );
        policy_mode
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn user_can_narrow_but_not_widen() {
        assert_eq!(narrow(Mode::OnPrem, Mode::AirGap), Mode::AirGap);
        assert_eq!(narrow(Mode::AirGap, Mode::Cloud), Mode::AirGap);
        assert_eq!(narrow(Mode::Cloud, Mode::OnPrem), Mode::OnPrem);
        assert_eq!(narrow(Mode::AirGap, Mode::AirGap), Mode::AirGap);
    }
}
