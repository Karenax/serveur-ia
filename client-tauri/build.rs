fn main() {
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("linux") {
        let config = std::fs::read_to_string("tauri.conf.json").expect("Configuration Tauri absente");
        let config: serde_json::Value = serde_json::from_str(&config).expect("Configuration Tauri invalide");
        let version = config.get("version").and_then(|v| v.as_str()).expect("Version Tauri absente");
        assert!(version.split('.').count() == 3 && version.split('.').all(|p| !p.is_empty() && p.len() <= 4 && p.bytes().all(|b| b.is_ascii_digit())), "Version Tauri invalide");
        println!("cargo:rustc-env=KIARA_LINUX_BUILD_VERSION={version}");
        println!("cargo:rerun-if-changed=tauri.conf.json");
    }
    tauri_build::build();
}
