// MattPaint for Mac and Windows: the web app in a native window, plus the few things a web page
// can't do on its own (see desktop.js for the page side).
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use base64::Engine;
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_opener::OpenerExt;

/// MATTPAINT_SELFTEST=<folder> runs the app as its own test: the window opens off screen, Save
/// writes into the folder instead of asking, Print and Wallpaper only record that they were
/// asked for, and a script drives the page and writes report.json there. See selftest.js.
fn selftest_dir() -> Option<std::path::PathBuf> {
    std::env::var_os("MATTPAINT_SELFTEST").map(Into::into)
}

fn decode(data: &str) -> Result<Vec<u8>, String> {
    base64::engine::general_purpose::STANDARD.decode(data).map_err(|e| e.to_string())
}

/// Save a picture where the person chooses, starting in Pictures with the name they typed.
/// Returns false if they cancelled.
#[tauri::command]
fn save_file(app: tauri::AppHandle, name: String, data: String) -> Result<bool, String> {
    let bytes = decode(&data)?;
    if let Some(dir) = selftest_dir() {
        std::fs::write(dir.join(&name), bytes).map_err(|e| e.to_string())?;
        return Ok(true);
    }
    let mut dialog = app.dialog().file().set_file_name(&name);
    if let Ok(dir) = app.path().picture_dir() {
        dialog = dialog.set_directory(dir);
    }
    let Some(path) = dialog.blocking_save_file() else { return Ok(false) };
    let path = path.into_path().map_err(|e| e.to_string())?;
    std::fs::write(&path, bytes).map_err(|e| e.to_string())?;
    Ok(true)
}

/// Make the picture the desktop wallpaper. It is kept in the app's own folder, since the
/// system reads the file again whenever it redraws the desktop.
#[tauri::command]
fn set_wallpaper(app: tauri::AppHandle, name: String, data: String) -> Result<bool, String> {
    let bytes = decode(&data)?;
    if let Some(dir) = selftest_dir() {
        std::fs::write(dir.join(format!("wallpaper-{name}")), bytes).map_err(|e| e.to_string())?;
        return Ok(true);
    }
    let dir = app.path().app_data_dir().map_err(|e| e.to_string())?.join("wallpapers");
    std::fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    let file = std::path::Path::new(&name).file_name().map(|n| n.to_owned()).unwrap_or_else(|| "wallpaper.png".into());
    let path = dir.join(file);
    std::fs::write(&path, bytes).map_err(|e| e.to_string())?;
    wallpaper::set_from_path(&path.to_string_lossy()).map_err(|e| e.to_string())?;
    Ok(true)
}

#[tauri::command]
fn print_page(window: tauri::WebviewWindow) -> Result<(), String> {
    if let Some(dir) = selftest_dir() {
        return std::fs::write(dir.join("print.txt"), "print asked for").map_err(|e| e.to_string());
    }
    window.print().map_err(|e| e.to_string())
}

#[tauri::command]
fn selftest_report(app: tauri::AppHandle, report: String) {
    if let Some(dir) = selftest_dir() {
        let _ = std::fs::write(dir.join("report.json"), report);
    }
    app.exit(0);
}

#[tauri::command]
fn quit(app: tauri::AppHandle) {
    app.exit(0);
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![save_file, set_wallpaper, print_page, selftest_report, quit])
        .setup(|app| {
            let handle = app.handle().clone();
            let mut builder = WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()));
            if selftest_dir().is_some() {
                builder = builder.position(-4000.0, 100.0).focused(false).initialization_script(include_str!("../../selftest.js"));
            }
            builder
                .title("MattPaint")
                .inner_size(1280.0, 820.0)
                .min_inner_size(640.0, 480.0)
                // Email (mailto:) and web links open in the person's own apps, never inside
                // the paint window.
                .on_navigation(move |url| {
                    let local = matches!(url.scheme(), "tauri" | "asset" | "about" | "data" | "blob")
                        || url.host_str().is_some_and(|h| h == "tauri.localhost" || h == "localhost");
                    if !local {
                        let _ = handle.opener().open_url(url.as_str(), None::<&str>);
                    }
                    local
                })
                .build()?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("MattPaint failed to start");
}
