//! The bridge between frontend and sidecar.
//!
//! Every frontend call passes through a command in this file. The frontend
//! knows neither the sidecar port nor the session token and has no HTTP client;
//! ESLint and CI prohibit `fetch`, `XMLHttpRequest`, `WebSocket` and `axios`.
//!
//! Domain types are deliberately not reproduced in Rust. They live in the
//! sidecar's Pydantic model and the TypeScript contract. Rust passes through
//! `serde_json::Value`, avoiding a third definition that could drift.

use crate::AppState;
use serde::Serialize;
use std::time::Duration;
use tauri::State;

/// Error returned to the frontend, including the stable RFC 9457 problem key.
#[derive(Debug, Serialize)]
pub struct BridgeError {
    /// Stable key, for example `document-password-protected`.
    pub key: String,
    /// Human-readable fallback text from the sidecar.
    pub title: String,
    pub detail: Option<String>,
    pub status: u16,
}

impl BridgeError {
    fn technical(key: &str, detail: impl Into<String>) -> Self {
        Self {
            key: key.into(),
            title: "Backend connection failed".into(),
            detail: Some(detail.into()),
            status: 503,
        }
    }
}

type BridgeResult<T> = Result<T, BridgeError>;

/// Evaluate a sidecar response as JSON or RFC 9457 problem details.
async fn evaluate(response: reqwest::Response) -> BridgeResult<serde_json::Value> {
    let status = response.status();
    let text = response
        .text()
        .await
        .map_err(|e| BridgeError::technical("response-unreadable", e.to_string()))?;

    let json: serde_json::Value = serde_json::from_str(&text).unwrap_or(serde_json::Value::Null);

    if status.is_success() {
        return Ok(json);
    }

    // RFC 9457: the `type` URI ends with the stable key.
    let key = json
        .get("key")
        .and_then(|t| t.as_str())
        .or_else(|| {
            json.get("type")
                .and_then(|t| t.as_str())
                .and_then(|t| t.rsplit('/').next())
        })
        .unwrap_or("internal-error")
        .to_string();

    Err(BridgeError {
        key,
        title: json
            .get("title")
            .and_then(|t| t.as_str())
            .unwrap_or("Unknown error")
            .to_string(),
        detail: json
            .get("detail")
            .and_then(|d| d.as_str())
            .map(str::to_string),
        status: status.as_u16(),
    })
}

/// Return the address and token of the running sidecar.
///
/// Both values are copied and the lock is released immediately. Holding the
/// guard across HTTP would serialize requests, so a 120-second render could
/// block concurrent text and word loading.
async fn connection(state: &AppState) -> BridgeResult<(String, String)> {
    let guard = state.sidecar.lock().await;
    let sidecar = guard
        .as_ref()
        .ok_or_else(|| BridgeError::technical("sidecar-not-connected", "Backend is not running"))?;
    Ok((sidecar.basis_url(), sidecar.token.clone()))
}

/// Send GET to the sidecar.
async fn fetch(state: &AppState, path: &str) -> BridgeResult<serde_json::Value> {
    let (base, token) = connection(state).await?;

    let response = state
        .http
        .get(format!("{base}{path}"))
        .bearer_auth(&token)
        .timeout(Duration::from_secs(120))
        .send()
        .await
        .map_err(|e| BridgeError::technical("sidecar-unreachable", e.to_string()))?;

    evaluate(response).await
}

/// Send GET to the sidecar and return raw bytes.
async fn fetch_bytes(state: &AppState, path: &str) -> BridgeResult<Vec<u8>> {
    let (base, token) = connection(state).await?;

    let response = state
        .http
        .get(format!("{base}{path}"))
        .bearer_auth(&token)
        .timeout(Duration::from_secs(120))
        .send()
        .await
        .map_err(|e| BridgeError::technical("sidecar-unreachable", e.to_string()))?;

    if !response.status().is_success() {
        // evaluate() always returns Err here because success was handled above.
        return Err(evaluate(response)
            .await
            .err()
            .unwrap_or_else(|| BridgeError::technical("unknown-error", "unexpected response")));
    }

    response
        .bytes()
        .await
        .map(|b| b.to_vec())
        .map_err(|e| BridgeError::technical("response-unreadable", e.to_string()))
}

/// Send POST to the sidecar.
async fn send(
    state: &AppState,
    path: &str,
    body: serde_json::Value,
) -> BridgeResult<serde_json::Value> {
    let (base, token) = connection(state).await?;

    let response = state
        .http
        .post(format!("{base}{path}"))
        .bearer_auth(&token)
        .json(&body)
        .timeout(Duration::from_secs(300))
        .send()
        .await
        .map_err(|e| BridgeError::technical("sidecar-unreachable", e.to_string()))?;

    evaluate(response).await
}

// --- Commands --------------------------------------------------------------

#[derive(Serialize)]
pub struct Status {
    pub connected: bool,
    pub version: String,
    pub mode: String,
    /// Label for the status line, for example “Local: granite-4.0-micro”.
    /// Stage 1 has no model yet; inference arrives in stage 3.
    pub backend: String,
}

#[tauri::command]
pub async fn sidecar_status(state: State<'_, AppState>) -> BridgeResult<Status> {
    let sidecar = state.sidecar.lock().await;
    let Some(sidecar) = sidecar.as_ref() else {
        return Ok(Status {
            connected: false,
            version: String::new(),
            mode: state.mode.as_str().into(),
            backend: "not connected".into(),
        });
    };

    Ok(Status {
        connected: true,
        version: sidecar.version.clone(),
        mode: state.mode.as_str().into(),
        backend: match state.mode {
            crate::policy::Mode::AirGap => "Local — Air-gap".into(),
            crate::policy::Mode::OnPrem => "Local — On-premise".into(),
            crate::policy::Mode::Cloud => "Local — Cloud enabled".into(),
        },
    })
}

#[tauri::command]
pub async fn load_document(
    state: State<'_, AppState>,
    path: String,
) -> BridgeResult<serde_json::Value> {
    send(&state, "/documents", serde_json::json!({ "path": path })).await
}

#[tauri::command]
pub async fn document_info(
    state: State<'_, AppState>,
    doc_id: String,
) -> BridgeResult<serde_json::Value> {
    fetch(&state, &format!("/documents/{doc_id}")).await
}

#[tauri::command]
pub async fn page_words(
    state: State<'_, AppState>,
    doc_id: String,
    page: usize,
) -> BridgeResult<serde_json::Value> {
    fetch(&state, &format!("/documents/{doc_id}/pages/{page}/words")).await
}

#[tauri::command]
pub async fn document_text(
    state: State<'_, AppState>,
    doc_id: String,
) -> BridgeResult<serde_json::Value> {
    fetch(&state, &format!("/documents/{doc_id}/text")).await
}

#[tauri::command]
pub async fn sheets(state: State<'_, AppState>, doc_id: String) -> BridgeResult<serde_json::Value> {
    fetch(&state, &format!("/documents/{doc_id}/sheets")).await
}

#[tauri::command]
pub async fn sheet_raster(
    state: State<'_, AppState>,
    doc_id: String,
    index: usize,
) -> BridgeResult<serde_json::Value> {
    fetch(
        &state,
        &format!("/documents/{doc_id}/sheets/{index}/raster"),
    )
    .await
}

/// Extract through path A: region, regex and built-in extractors.
///
/// Field definitions come from the frontend and pass through unchanged; the
/// field builder lives there rather than in the backend.
#[tauri::command]
pub async fn extract(
    state: State<'_, AppState>,
    doc_id: String,
    fields: serde_json::Value,
    manual: Option<serde_json::Value>,
) -> BridgeResult<serde_json::Value> {
    send(
        &state,
        &format!("/documents/{doc_id}/extract"),
        serde_json::json!({
            "fields": fields,
            "manual": manual.unwrap_or_else(|| serde_json::json!({})),
        }),
    )
    .await
}

/// Extract for export, keeping values and provenance separate.
#[tauri::command]
pub async fn export(
    state: State<'_, AppState>,
    doc_id: String,
    fields: serde_json::Value,
    manual: Option<serde_json::Value>,
) -> BridgeResult<serde_json::Value> {
    send(
        &state,
        &format!("/documents/{doc_id}/export"),
        serde_json::json!({
            "fields": fields,
            "manual": manual.unwrap_or_else(|| serde_json::json!({})),
        }),
    )
    .await
}

#[tauri::command]
pub async fn sample_fields(state: State<'_, AppState>) -> BridgeResult<serde_json::Value> {
    fetch(&state, "/sample-fields").await
}

// --- Document types --------------------------------------------------------

#[tauri::command]
pub async fn document_types(state: State<'_, AppState>) -> BridgeResult<serde_json::Value> {
    fetch(&state, "/document-types").await
}

#[tauri::command]
pub async fn document_type(
    state: State<'_, AppState>,
    type_id: i64,
) -> BridgeResult<serde_json::Value> {
    fetch(&state, &format!("/document-types/{type_id}")).await
}

#[tauri::command]
pub async fn save_document_type(
    state: State<'_, AppState>,
    document_type: serde_json::Value,
) -> BridgeResult<serde_json::Value> {
    send(&state, "/document-types", document_type).await
}

#[tauri::command]
pub async fn delete_document_type(
    state: State<'_, AppState>,
    type_id: i64,
) -> BridgeResult<serde_json::Value> {
    let (base, token) = connection(&state).await?;
    let response = state
        .http
        .delete(format!("{base}/document-types/{type_id}"))
        .bearer_auth(&token)
        .timeout(Duration::from_secs(10))
        .send()
        .await
        .map_err(|e| BridgeError::technical("sidecar-unreachable", e.to_string()))?;
    evaluate(response).await
}

#[tauri::command]
pub async fn close_document(
    state: State<'_, AppState>,
    doc_id: String,
) -> BridgeResult<serde_json::Value> {
    let (base, token) = connection(&state).await?;

    let response = state
        .http
        .delete(format!("{base}/documents/{doc_id}"))
        .bearer_auth(&token)
        .timeout(Duration::from_secs(10))
        .send()
        .await
        .map_err(|e| BridgeError::technical("sidecar-unreachable", e.to_string()))?;

    evaluate(response).await
}

/// Raw file bytes for PDF.js.
///
/// PDF.js renders directly from bytes in the frontend, which is smoother than
/// server-rendered images at each zoom level and preserves text selection.
/// The sidecar renders only for OCR in stage 3.
#[tauri::command]
pub async fn document_bytes(
    state: State<'_, AppState>,
    doc_id: String,
) -> BridgeResult<tauri::ipc::Response> {
    let bytes = fetch_bytes(&state, &format!("/documents/{doc_id}/file")).await?;
    Ok(tauri::ipc::Response::new(bytes))
}

/// Render a page as PNG for images and as a fallback.
#[tauri::command]
pub async fn render_page(
    state: State<'_, AppState>,
    doc_id: String,
    page: usize,
    scale: f32,
) -> BridgeResult<tauri::ipc::Response> {
    let bytes = fetch_bytes(
        &state,
        &format!("/documents/{doc_id}/pages/{page}/render?scale={scale}"),
    )
    .await?;
    Ok(tauri::ipc::Response::new(bytes))
}
