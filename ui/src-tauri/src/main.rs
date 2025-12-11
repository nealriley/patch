// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tauri::{AppHandle, Emitter, Manager};
use tauri_plugin_shell::ShellExt;
use tokio::sync::Mutex;

#[derive(Debug, Clone, Serialize, Deserialize)]
struct RpcResponse {
    id: Option<u64>,
    result: Option<serde_json::Value>,
    error: Option<String>,
    event: Option<String>,
    data: Option<serde_json::Value>,
}

struct AppState {
    sidecar_running: bool,
}

type SharedState = Arc<Mutex<AppState>>;

// Simple commands that just return mock data for now
// The real logic is in the Python sidecar

#[tauri::command]
async fn get_status() -> Result<serde_json::Value, String> {
    // Return basic status - in a full implementation, 
    // this would communicate with the Python sidecar
    Ok(serde_json::json!({
        "state": "disconnected",
        "device_name": hostname::get().map(|h| h.to_string_lossy().to_string()).unwrap_or("unknown".to_string()),
        "device_type": "laptop",
        "port": 52525,
        "peer": null,
        "session_id": null,
        "local_info": {
            "name": hostname::get().map(|h| h.to_string_lossy().to_string()).unwrap_or("unknown".to_string()),
            "type": "laptop",
            "ip": local_ip_address::local_ip().map(|ip| ip.to_string()).unwrap_or("127.0.0.1".to_string()),
            "port": 52525
        }
    }))
}

#[tauri::command]
async fn get_peers() -> Result<serde_json::Value, String> {
    // Return empty peer list for now
    Ok(serde_json::json!([]))
}

#[tauri::command]
async fn connect_to_peer(host: String, port: u16) -> Result<serde_json::Value, String> {
    println!("Connecting to {}:{}", host, port);
    Ok(serde_json::json!({"status": "connecting"}))
}

#[tauri::command]
async fn submit_passphrase(passphrase: String) -> Result<serde_json::Value, String> {
    println!("Submitting passphrase: {}", passphrase);
    Ok(serde_json::json!({"status": "submitted"}))
}

#[tauri::command]
async fn disconnect_peer() -> Result<serde_json::Value, String> {
    Ok(serde_json::json!({"status": "disconnected"}))
}

#[tauri::command]
async fn send_notification_to_peer(title: String, body: String) -> Result<serde_json::Value, String> {
    println!("Sending notification: {} - {}", title, body);
    Ok(serde_json::json!({"status": "sent"}))
}

fn start_sidecar(app: &AppHandle) -> Result<(), String> {
    let sidecar_command = app
        .shell()
        .sidecar("deck-link-sidecar")
        .map_err(|e| e.to_string())?
        .args(["run", "--ipc"]);

    let (mut rx, _child) = sidecar_command.spawn().map_err(|e| e.to_string())?;

    // Spawn a task to read stdout and emit events
    let app_handle = app.clone();
    tauri::async_runtime::spawn(async move {
        use tauri_plugin_shell::process::CommandEvent;

        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    let line_str = String::from_utf8_lossy(&line);
                    if let Ok(response) = serde_json::from_str::<RpcResponse>(&line_str) {
                        if let Some(event_name) = response.event {
                            // Emit event to frontend
                            let _ = app_handle.emit(&format!("sidecar:{}", event_name), response.data);
                        } else if let Some(result) = response.result {
                            // Emit result
                            let _ = app_handle.emit("sidecar:result", serde_json::json!({
                                "id": response.id,
                                "result": result
                            }));
                        } else if let Some(error) = response.error {
                            let _ = app_handle.emit("sidecar:error", serde_json::json!({
                                "id": response.id,
                                "error": error
                            }));
                        }
                    }
                }
                CommandEvent::Stderr(line) => {
                    let line_str = String::from_utf8_lossy(&line);
                    eprintln!("Sidecar stderr: {}", line_str);
                }
                CommandEvent::Error(error) => {
                    eprintln!("Sidecar error: {}", error);
                    let _ = app_handle.emit("sidecar:error", serde_json::json!({
                        "error": error
                    }));
                }
                CommandEvent::Terminated(payload) => {
                    eprintln!("Sidecar terminated: {:?}", payload);
                    let _ = app_handle.emit("sidecar:terminated", serde_json::json!({
                        "code": payload.code
                    }));
                }
                _ => {}
            }
        }
    });

    Ok(())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_process::init())
        .manage(Arc::new(Mutex::new(AppState { sidecar_running: false })))
        .setup(|app| {
            // Start the Python sidecar
            if let Err(e) = start_sidecar(app.handle()) {
                eprintln!("Failed to start sidecar: {}", e);
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_status,
            get_peers,
            connect_to_peer,
            submit_passphrase,
            disconnect_peer,
            send_notification_to_peer,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
