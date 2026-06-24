#[tauri::command]
fn save_download(bytes: Vec<u8>, suggested_name: String) -> Result<Option<String>, String> {
    let path = rfd::FileDialog::new()
        .set_file_name(&suggested_name)
        .save_file();
    match path {
        Some(target) => {
            std::fs::write(&target, bytes).map_err(|error| error.to_string())?;
            Ok(Some(target.to_string_lossy().into_owned()))
        }
        None => Ok(None),
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![save_download])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
