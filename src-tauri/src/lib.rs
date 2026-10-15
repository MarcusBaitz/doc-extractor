//! Substrakt — Tauri shell.
//!
//! This shell starts the Python sidecar, owns the sole egress chokepoint and
//! provides the frontend bridge to the backend. The frontend has no network
//! access of its own.

pub mod bridge;
pub mod egress;
pub mod policy;
pub mod sidecar;

use egress::Egress;
use policy::Mode;
use sidecar::Sidecar;
use std::sync::Arc;
use tauri::Manager;
use tokio::sync::Mutex;

pub struct AppState {
    pub sidecar: Mutex<Option<Sidecar>>,
    pub http: reqwest::Client,
    pub mode: Mode,
    pub egress: Arc<Egress>,
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let (mode, policy) = policy::load();
    log::info!("Operating mode: {}", mode.as_str());

    // The HTTP client talks only to 127.0.0.1. Proxy detection is disabled:
    // an environment variable such as `HTTP_PROXY` could otherwise route
    // local sidecar traffic through another machine.
    let http = reqwest::Client::builder()
        .no_proxy()
        .user_agent(concat!("Substrakt/", env!("CARGO_PKG_VERSION")))
        .build()
        .expect("HTTP client could not be created");

    let egress = Arc::new(Egress::new(
        mode,
        policy.allowlist.clone(),
        policy.inference_server.clone(),
    ));

    tauri::Builder::default()
        .plugin(
            // Rotating and local. Logs contain hashes, field names and metrics,
            // never document contents; see docs/decisions.md.
            tauri_plugin_log::Builder::new()
                .targets([
                    tauri_plugin_log::Target::new(tauri_plugin_log::TargetKind::Stdout),
                    tauri_plugin_log::Target::new(tauri_plugin_log::TargetKind::LogDir {
                        file_name: Some("substrakt".into()),
                    }),
                ])
                .max_file_size(5 * 1024 * 1024)
                .rotation_strategy(tauri_plugin_log::RotationStrategy::KeepAll)
                .level(if cfg!(debug_assertions) {
                    log::LevelFilter::Debug
                } else {
                    log::LevelFilter::Info
                })
                .build(),
        )
        .plugin(tauri_plugin_dialog::init())
        .manage(AppState {
            sidecar: Mutex::new(None),
            http: http.clone(),
            mode,
            egress,
        })
        .invoke_handler(tauri::generate_handler![
            bridge::sidecar_status,
            bridge::load_document,
            bridge::document_info,
            bridge::document_bytes,
            bridge::document_text,
            bridge::close_document,
            bridge::page_words,
            bridge::render_page,
            bridge::sheets,
            bridge::sheet_raster,
            bridge::extract,
            bridge::export,
            bridge::sample_fields,
            bridge::document_types,
            bridge::document_type,
            bridge::save_document_type,
            bridge::delete_document_type,
        ])
        .setup(move |app| {
            let handle = app.handle().clone();
            let data_dir = app
                .path()
                .app_data_dir()
                .unwrap_or_else(|_| std::path::PathBuf::from("."));
            let resources = app.path().resource_dir().ok();

            tauri::async_runtime::spawn(async move {
                let state = handle.state::<AppState>();
                match sidecar::start(resources, data_dir, mode.as_str(), &state.http).await {
                    Ok(sidecar) => {
                        log::info!("Sidecar connected on port {}", sidecar.port);
                        *state.sidecar.lock().await = Some(sidecar);
                    }
                    Err(error) => {
                        // The application cannot process documents without the
                        // sidecar, but it stays open and exposes the cause.
                        log::error!("Sidecar start failed: {error}");
                    }
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if matches!(event, tauri::WindowEvent::Destroyed) {
                let handle = window.app_handle().clone();
                tauri::async_runtime::block_on(async move {
                    let state = handle.state::<AppState>();

                    // Taking the guard in its own statement releases it before
                    // shutdown. An `if let` scrutinee would keep it alive until
                    // the end of the block and outlive `state`.
                    let sidecar = state.sidecar.lock().await.take();

                    if let Some(sidecar) = sidecar {
                        sidecar.shutdown(&state.http).await;
                    }
                });
            }
        })
        .run(tauri::generate_context!())
        .expect("Application could not be started");
}
