#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    io::{BufRead, BufReader, Read, Write},
    os::windows::process::CommandExt,
    path::{Path, PathBuf},
    process::{Child, ChildStdin, Command, Stdio},
    sync::{atomic::{AtomicBool, Ordering}, mpsc, Arc, Mutex},
    thread,
    time::{Duration, Instant},
};
use tauri::{Url, WebviewUrl, WebviewWindow, WebviewWindowBuilder, WindowEvent};

type RelayInput = Arc<Mutex<Option<ChildStdin>>>;

struct Relay(Child, RelayInput);

impl Drop for Relay {
    fn drop(&mut self) {
        drop(self.1.lock().unwrap().take());
        let deadline = Instant::now() + Duration::from_secs(5);
        while Instant::now() < deadline {
            if matches!(self.0.try_wait(), Ok(Some(_))) {
                return;
            }
            thread::sleep(Duration::from_millis(50));
        }
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}

fn relay_ready(line: &str) -> Result<(Url, String), &'static str> {
    let (url, identity) = line.strip_prefix("KIARA_RELAY_READY ")
        .and_then(|value| value.split_once(' '))
        .ok_or("Le relais Kiara n’a pas pu ouvrir le profil")?;
    if identity.len() != 20 || !identity.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err("Identifiant de profil Kiara invalide");
    }
    Ok((local_url(url)?, identity.to_owned()))
}

fn start_relay(profile: Option<&Path>, version: &str) -> Result<Option<(Url, String, Relay, mpsc::Receiver<String>)>, &'static str> {
    let executable = std::env::current_exe().map_err(|_| "Emplacement de Kiara introuvable")?;
    let binary = executable.with_file_name("kiara-relay.exe");
    let mut command = Command::new(binary);
    command.arg("--relay-stdio");
    command.env("KIARA_DESKTOP_VERSION", version);
    command.env("KIARA_DESKTOP_UPDATES", "1");
    if let Some(profile) = profile {
        command.arg(profile);
    }
    let mut child = command
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .creation_flags(0x08000000)
        .spawn().map_err(|_| "Impossible de démarrer le relais Kiara")?;
    let input = child.stdin.take();
    let mut relay = Relay(child, Arc::new(Mutex::new(input)));
    let output = relay.0.stdout.take().ok_or("Le relais Kiara ne répond pas")?;
    let (send, receive) = mpsc::sync_channel(1);
    thread::spawn(move || {
        let mut output = BufReader::new(output);
        loop {
            let mut line = String::new();
            if !matches!(output.by_ref().take(8192).read_line(&mut line), Ok(count) if count > 0)
                || !line.ends_with('\n')
                || send.send(line).is_err()
            {
                break;
            }
        }
    });
    let first = receive.recv_timeout(Duration::from_secs(45))
        .map_err(|_| "Le relais Kiara ne répond pas")?;
    let response = if first.trim_end() == "KIARA_RELAY_SELECT_PROFILE" {
        receive.recv().map_err(|_| "Le relais Kiara n’a pas pu ouvrir le profil")?
    } else {
        first
    };
    if response.trim_end() == "KIARA_RELAY_CANCELLED" {
        return Ok(None);
    }
    let (url, identity) = relay_ready(response.trim_end())?;
    Ok(Some((url, identity, relay, receive)))
}

fn local_url(value: &str) -> Result<Url, &'static str> {
    let url = Url::parse(value).map_err(|_| "Adresse locale invalide")?;
    if url.scheme() != "http"
        || url.host_str() != Some("127.0.0.1")
        || !url.username().is_empty()
        || url.password().is_some()
        || !matches!(url.port(), Some(1024..=65535))
        || url.path() != "/chat"
        || url.query().is_some()
        || url.fragment().is_some()
    {
        return Err("Adresse locale invalide");
    }
    Ok(url)
}

const PREPARE_CLOSE: &str = r#"
    if (window.kiaraCloseStatus !== 'pending') {
        window.kiaraCloseStatus = 'pending';
        (async () => {
            if (location.pathname === '/chat' || location.pathname === '/') {
                await window.kiaraPrepareClose();
            } else if (!window.dispatchEvent(new Event('beforeunload', {cancelable: true}))) {
                throw new Error();
            }
            window.kiaraCloseStatus = 'ready';
        })().catch(problem => {
            window.kiaraCloseStatus = 'failed';
            if (typeof error === 'function') error(problem);
        });
    }
"#;

fn wait_for_close_save(window: &WebviewWindow) -> bool {
    if window.eval(PREPARE_CLOSE).is_err() {
        return false;
    }
    let deadline = Instant::now() + Duration::from_secs(300);
    while Instant::now() < deadline {
        let (send, receive) = mpsc::sync_channel(1);
        if window.eval_with_callback("window.kiaraCloseStatus", move |state| {
            let _ = send.send(state);
        }).is_err() {
            return false;
        }
        match receive.recv_timeout(Duration::from_secs(2)).as_deref() {
            Ok("\"ready\"") => return true,
            Ok("\"pending\"") => thread::sleep(Duration::from_millis(100)),
            _ => return false,
        }
    }
    false
}

fn confirm_close(window: &WebviewWindow) -> bool {
    #[link(name = "user32")]
    extern "system" {
        fn MessageBoxW(owner: *mut std::ffi::c_void, text: *const u16, title: *const u16, flags: u32) -> i32;
    }
    let Ok(owner) = window.hwnd() else { return false; };
    let text: Vec<u16> = "Des modifications peuvent être en attente. Fermer Kiara quand même ?"
        .encode_utf16().chain([0]).collect();
    let title: Vec<u16> = "Fermer Kiara".encode_utf16().chain([0]).collect();
    const YES_NO_WARNING_DEFAULT_NO: u32 = 0x0004 | 0x0030 | 0x0100;
    const YES: i32 = 6;
    // The buffers stay alive while the modal dialog is open on the window thread.
    unsafe { MessageBoxW(owner.0, text.as_ptr(), title.as_ptr(), YES_NO_WARNING_DEFAULT_NO) == YES }
}

fn protect_close(window: &WebviewWindow, pending: Arc<AtomicBool>) {
    let registered = window.clone();
    window.on_window_event(move |event| {
        let WindowEvent::CloseRequested { api, .. } = event else { return; };
        api.prevent_close();
        if pending.swap(true, Ordering::AcqRel) {
            return;
        }
        let window = registered.clone();
        let pending = pending.clone();
        thread::spawn(move || {
            let saved = wait_for_close_save(&window);
            let callback_window = window.clone();
            let callback_pending = pending.clone();
            if window.run_on_main_thread(move || {
                if saved || confirm_close(&callback_window) {
                    let _ = callback_window.destroy();
                }
                callback_pending.store(false, Ordering::Release);
            }).is_err() {
                pending.store(false, Ordering::Release);
            }
        });
    });
}

fn relay_reply(input: &RelayInput, reply: u8) {
    if let Some(stream) = input.lock().unwrap().as_mut() {
        let _ = stream.write_all(&[reply]);
    }
}

fn update_installer(line: &str) -> Option<&Path> {
    let value = line.strip_suffix('\n')?.trim_end_matches('\r');
    let path = Path::new(value.strip_prefix("KIARA_RELAY_UPDATE ")?);
    let release = path.file_name()?.to_str()?.strip_prefix("Kiara_4.")?.strip_suffix("_x64-setup.exe")?;
    let (minor, patch) = release.split_once('.')?;
    if !path.is_absolute() || [minor, patch].iter().any(|part| {
        part.is_empty() || part.len() > 4 || !part.bytes().all(|byte| byte.is_ascii_digit())
    }) {
        return None;
    }
    Some(path)
}

fn watch_updates(window: &WebviewWindow, pending: Arc<AtomicBool>, input: RelayInput, events: mpsc::Receiver<String>) {
    let window = window.clone();
    thread::spawn(move || {
        for event in events {
            let Some(installer) = update_installer(&event) else { continue; };
            if pending.swap(true, Ordering::AcqRel) {
                relay_reply(&input, b'c');
                continue;
            }
            if !wait_for_close_save(&window) {
                relay_reply(&input, b'c');
                pending.store(false, Ordering::Release);
                continue;
            }
            let handle = window.clone();
            let input_for_window = input.clone();
            let pending_for_window = pending.clone();
            let installer = installer.to_owned();
            if window.run_on_main_thread(move || {
                // The installer waits for this process and its relay to finish closing.
                let started = Command::new(&installer)
                    .args(["/P", "/UPDATE", "/R"])
                    .arg(format!("/KIARA-WAIT={}", std::process::id()))
                    .stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null())
                    .spawn().is_ok();
                relay_reply(&input_for_window, if started { b'u' } else { b'c' });
                if started {
                    let _ = handle.destroy();
                }
                pending_for_window.store(false, Ordering::Release);
            }).is_err() {
                relay_reply(&input, b'c');
                pending.store(false, Ordering::Release);
            }
        }
    });
}

fn main() {
    let context = tauri::generate_context!();
    let args: Vec<_> = std::env::args_os().collect();
    let mut relay = None;
    let mut updates = None;
    let mut profile_directory = None;
    let (url, hidden) = match args.as_slice() {
        [_, flag, value] if flag == "--local-url" => (local_url(&value.to_string_lossy()), false),
        [_, flag, value, hidden] if flag == "--local-url" && hidden == "--hidden" => {
            (local_url(&value.to_string_lossy()), true)
        }
        arguments => {
            let (profile, hidden) = match arguments {
                [_] => (None, false),
                [_, hidden] if hidden == "--hidden" => (None, true),
                [_, flag, value] if flag == "--profile-exe" => (Some(Path::new(value)), false),
                [_, flag, value, hidden] if flag == "--profile-exe" && hidden == "--hidden" => {
                    (Some(Path::new(value)), true)
                }
                _ => { eprintln!("Paramètres Kiara invalides"); std::process::exit(2); }
            };
            match start_relay(profile, &context.package_info().version.to_string()) {
                Ok(Some((url, identity, child, events))) => {
                    updates = Some((child.1.clone(), events));
                    relay = Some(child);
                    profile_directory = Some(format!("webview-{identity}"));
                    (Ok(url), hidden)
                }
                Ok(None) => return,
                Err(message) => (Err(message), hidden),
            }
        }
    };
    let url = match url {
        Ok(url) => url,
        Err(message) => {
            eprintln!("{message}");
            std::process::exit(2);
        }
    };
    let origin = (
        url.scheme().to_owned(),
        url.host_str().unwrap().to_owned(),
        url.port(),
    );
    let app = tauri::Builder::default()
        .setup(move |app| {
            let mut builder = WebviewWindowBuilder::new(app, "main", WebviewUrl::External(url.clone()))
                .title("Kiara")
                .visible(!hidden)
                .inner_size(1280.0, 800.0)
                .min_inner_size(600.0, 450.0)
                .on_navigation(move |next| {
                    next.scheme() == origin.0
                        && next.host_str() == Some(origin.1.as_str())
                        && next.port() == origin.2
                });
            if let (Some(local_app_data), Some(directory)) = (std::env::var_os("LOCALAPPDATA"), profile_directory) {
                builder = builder.data_directory(PathBuf::from(local_app_data).join("QwenClient").join(directory));
            }
            let window = builder.build()?;
            if let Some((input, events)) = updates {
                let pending = Arc::new(AtomicBool::new(false));
                protect_close(&window, pending.clone());
                watch_updates(&window, pending, input, events);
            }
            Ok(())
        })
        .build(context)
        .expect("Impossible de démarrer Kiara");
    let exit_code = app.run_return(|_, _| {});
    drop(relay);
    std::process::exit(exit_code);
}

#[cfg(test)]
mod tests {
    use super::{local_url, relay_ready, update_installer};

    #[test]
    fn only_accepts_a_windows_installer_from_the_relay() {
        assert!(update_installer("KIARA_RELAY_UPDATE C:\\Usér Files\\Kiara_4.0.2_x64-setup.exe\r\n").is_some());
        assert!(update_installer("KIARA_RELAY_UPDATE C:\\Kiara_3.5.63_x64-setup.exe\n").is_none());
        assert!(update_installer("KIARA_RELAY_UPDATE Kiara_4.0.2_x64-setup.exe\n").is_none());
    }

    #[test]
    fn relay_supplies_a_local_origin_and_safe_profile_directory_key() {
        let (url, key) = relay_ready("KIARA_RELAY_READY http://127.0.0.1:45678/chat 0123456789abcdef0123").unwrap();
        assert_eq!(url.port(), Some(45678));
        assert_eq!(key, "0123456789abcdef0123");
        assert!(relay_ready("KIARA_RELAY_READY http://127.0.0.1:45678/chat ../another-profile").is_err());
    }

    #[test]
    fn only_accepts_the_local_client_chat_origin() {
        assert!(local_url("http://127.0.0.1:45678/chat").is_ok());
        for value in [
            "http://example.com:45678/chat",
            "http://localhost:45678/chat",
            "http://user@127.0.0.1:45678/chat",
            "http://127.0.0.1:45678/app",
            "http://127.0.0.1:45678/chat?token=secret",
            "https://127.0.0.1:45678/chat",
        ] {
            assert!(local_url(value).is_err(), "{value}");
        }
    }
}
