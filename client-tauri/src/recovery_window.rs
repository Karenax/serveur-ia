//! Isolated recovery window for a future profile-locked startup flow.
//! The normal window retains its single-origin navigation policy.
use std::path::PathBuf;
use tauri::{AppHandle, Url, WebviewUrl, WebviewWindow, WebviewWindowBuilder};

use crate::recovery_policy::RecoveryOrigins;
use crate::recovery_protocol::{RecoveryOffer, TransferOffer};

fn initialization_script(token: &str, origins: &RecoveryOrigins) -> String {
    let ports = origins.ports().iter().map(|port| port.to_string()).collect::<Vec<_>>().join(",");
    include_str!("recovery_init.js")
        .replace("__TOKEN__", token)
        .replace("__PORTS__", &ports)
        .replace("__REQUIRE_NAVIGATION__", if cfg!(windows) { "true" } else { "false" })
}

/// The caller holds the profile lock, reserves all ports, and owns window closure.
pub fn build(app: &AppHandle, offer: &RecoveryOffer, data_directory: PathBuf, hidden: bool)
    -> tauri::Result<WebviewWindow> {
    let policy = RecoveryOrigins::standard();
    let url = Url::parse(&format!("http://127.0.0.1:{}/recovery/scan", policy.ports()[0])).expect("static recovery URL");
    let script = initialization_script(offer.token(), &policy);
    WebviewWindowBuilder::new(app, "origin-recovery", WebviewUrl::External(url))
        .title("Vérification des données Kiara")
        .visible(!hidden)
        .inner_size(640.0, 480.0)
        .data_directory(data_directory)
        .initialization_script(script)
        .on_new_window(|_, _| tauri::webview::NewWindowResponse::Deny)
        .on_navigation(move |next| policy.allows(next))
        .build()
}

/// Build only isolated transfer windows; on partial failure, close all of them.
/// The caller retains the profile lock and must close them before another job.
pub fn build_transfer(app: &AppHandle, offer: &TransferOffer, data_directory: PathBuf)
    -> tauri::Result<Vec<WebviewWindow>> {
    let policy = RecoveryOrigins::standard();
    let init = initialization_script(offer.token(), &policy);
    let mut windows: Vec<WebviewWindow> = Vec::new();
    let roles = if offer.manifest() {
        vec![("origin-transfer-destination", offer.destination(), "sender")]
    } else if offer.qt_source() {
        vec![("origin-transfer-destination", offer.destination(), "receiver")]
    } else {
        vec![("origin-transfer-source", offer.source(), "sender"),
             ("origin-transfer-destination", offer.destination(), "receiver")]
    };
    for (label, port, role) in roles {
        let url = Url::parse(&format!("http://127.0.0.1:{port}/recovery/transfer")).expect("validated recovery URL");
        let mode = if offer.manifest() { "manifest" } else if offer.snapshot() { "snapshot" } else { "transfer" };
        let script = format!("{init}\nObject.defineProperty(window,'__kiaraRecoveryRole',{{value:'{role}',configurable:false}});\nObject.defineProperty(window,'__kiaraRecoveryMode',{{value:'{mode}',configurable:false}});");
        let allowed = policy.clone();
        let result = WebviewWindowBuilder::new(app, label, WebviewUrl::External(url))
            .title("Récupération des données Kiara")
            .visible(false)
            .data_directory(data_directory.clone())
            .initialization_script(script)
            .on_new_window(|_, _| tauri::webview::NewWindowResponse::Deny)
            .on_navigation(move |next| allowed.allows(next))
            .build();
        match result {
            Ok(window) => windows.push(window),
            Err(error) => {
                for window in windows { let _ = window.destroy(); }
                return Err(error);
            }
        }
    }
    Ok(windows)
}

#[cfg(test)]
mod tests {
    use super::initialization_script;
    use crate::recovery_policy::RecoveryOrigins;
    use crate::recovery_protocol::parse_recovery_offer;

    #[test]
    fn prepares_only_the_validated_token_and_reserved_ports() {
        let line = format!("KIARA_RELAY_ORIGIN_SCAN {} {}\n", "a".repeat(20), "b".repeat(64));
        let offer = parse_recovery_offer(&line).unwrap();
        let script = initialization_script(offer.token(), &RecoveryOrigins::standard());
        assert!(script.contains(&"b".repeat(64)));
        assert!(script.contains("17841,17842,17843,17844,17845,17846,17847,17848,17849,17850"));
        assert!(!script.contains("__TOKEN__") && !script.contains("__PORTS__") && !script.contains("__REQUIRE_NAVIGATION__"));
    }
}
