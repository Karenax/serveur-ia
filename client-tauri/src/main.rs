#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod recovery_policy;
mod recovery_protocol;
mod recovery_window;

use std::{
    io::{BufRead, BufReader, Read, Write},
    path::{Path, PathBuf},
    process::{Child, ChildStdin, Command, Stdio},
    sync::{atomic::{AtomicBool, Ordering}, mpsc, Arc, Mutex},
    thread,
    time::{Duration, Instant},
};
#[cfg(windows)]
use std::os::windows::process::CommandExt;
use tauri::{Url, WebviewUrl, WebviewWindow, WebviewWindowBuilder, WindowEvent};

type RelayInput = Arc<Mutex<Option<ChildStdin>>>;

struct Relay(Child, RelayInput);

enum RelayStart {
    Ready(Url, String, Relay, mpsc::Receiver<String>),
    Recovery(recovery_protocol::RecoveryOffer, Relay, mpsc::Receiver<String>),
}

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
    let line = line.trim_end();
    match line {
        "KIARA_RELAY_ORIGIN_BUSY" => return Err("Le port utilisé par les données locales est occupé. Fermez l’application qui l’utilise, puis relancez Kiara."),
        "KIARA_RELAY_ORIGIN_INVALID" => return Err("Impossible de vérifier le port des données locales. Conservez les fichiers de ce poste et vérifiez la configuration avant de relancer Kiara."),
        "KIARA_RELAY_ORIGIN_MULTIPLE" => return Err("Des données locales existent à plusieurs emplacements ou ne correspondent pas à la connexion actuelle. Elles sont conservées. Demandez de l’aide avant de les modifier."),
        "KIARA_RELAY_SETTINGS_UNREADABLE" => return Err("Impossible de lire les réglages locaux. Le fichier original est conservé. Vérifiez votre accès au trousseau ou restaurez une copie valide."),
        "KIARA_RELAY_RECOVERY_UNAVAILABLE" => return Err("La vérification des données locales est interrompue ou un port nécessaire est occupé. Fermez les autres versions de Kiara puis réessayez. Vos données sont conservées."),
        "KIARA_RELAY_RECEIVER_UNAVAILABLE" => return Err("La récupération des données locales ne répond pas. Vos données restent sur cet appareil. Relancez Kiara ; si le problème persiste, demandez de l’aide avant de modifier ces données."),
        "KIARA_RELAY_RECOVERY_CONFLICT" => return Err("Des brouillons différents existent sur plusieurs origines. Ils sont conservés ; la récupération doit être vérifiée avant de continuer."),
        "KIARA_RELAY_RECOVERY_RESTART" => return Err("Les deux versions sont conservées. Relancez Kiara pour terminer leur vérification."),
        "KIARA_RELAY_ARCHIVE_UNAVAILABLE" => return Err("Une version conservée est introuvable ou illisible. Les autres versions restent sur cet appareil. Restaurez la copie depuis une sauvegarde avant de réessayer."),
        "KIARA_RELAY_QT_STORAGE" => return Err("Des données locales d’une ancienne version restent à vérifier. Elles sont conservées sur cet appareil."),
        _ => (),
    }
    let (url, identity) = line.strip_prefix("KIARA_RELAY_READY ")
        .and_then(|value| value.split_once(' '))
        .ok_or("Le relais Kiara n’a pas pu ouvrir le profil")?;
    if identity.len() != 20 || !identity.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err("Identifiant de profil Kiara invalide");
    }
    let url = local_url(url)?;
    if url.query().is_none() {
        return Err("Session de démarrage Kiara absente ou invalide");
    }
    Ok((url, identity.to_owned()))
}

fn start_relay(profile: Option<&Path>, version: &str) -> Result<Option<RelayStart>, &'static str> {
    let executable = std::env::current_exe().map_err(|_| "Emplacement de Kiara introuvable")?;
    let binary = executable.with_file_name(if cfg!(windows) { "kiara-relay.exe" } else { "kiara-relay" });
    let mut command = Command::new(binary);
    command.arg("--relay-stdio");
    command.env("KIARA_DESKTOP_VERSION", version);
    #[cfg(windows)]
    command.env("KIARA_DESKTOP_UPDATES", "1");
    if let Some(profile) = profile {
        command.arg(profile);
    }
    command.stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null());
    #[cfg(windows)]
    command.creation_flags(0x08000000);
    let mut child = command.spawn().map_err(|_| "Impossible de démarrer le relais Kiara")?;
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
    let response = match response.trim_end() {
        "KIARA_RELAY_PROFILE_IN_USE" => return Err("Le profil Kiara est déjà ouvert"),
        "KIARA_RELAY_PROFILE_LOCK_UNAVAILABLE" => return Err("Le profil Kiara ne peut pas être protégé"),
        "KIARA_RELAY_PROFILE_LOCKED" => receive.recv_timeout(Duration::from_secs(45))
            .map_err(|_| "Le relais Kiara n’a pas pu ouvrir le profil")?,
        _ => return Err("Le relais Kiara doit être mis à jour avant de continuer"),
    };
    if response.starts_with("KIARA_RELAY_ORIGIN_SCAN ") {
        let offer = recovery_protocol::parse_recovery_offer(&response)
            .ok_or("Impossible de vérifier les données locales")?;
        return Ok(Some(RelayStart::Recovery(offer, relay, receive)));
    }
    let (url, identity) = relay_ready(response.trim_end())?;
    Ok(Some(RelayStart::Ready(url, identity, relay, receive)))
}

fn local_url(value: &str) -> Result<Url, &'static str> {
    let url = Url::parse(value).map_err(|_| "Adresse locale invalide")?;
    if url.scheme() != "http"
        || url.host_str() != Some("127.0.0.1")
        || !url.username().is_empty()
        || url.password().is_some()
        || !matches!(url.port(), Some(1024..=65535))
        || url.path() != "/chat"
        || url.query().is_some_and(|query| !query.strip_prefix("launch=").is_some_and(|token| {
            token.len() == 64 && token.bytes().all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
        }))
        || url.fragment().is_some()
    {
        return Err("Adresse locale invalide");
    }
    Ok(url)
}

fn diagnostic_url(value: &str) -> Result<Url, &'static str> {
    let url = local_url(value)?;
    if url.query().is_some() { return Err("Adresse de diagnostic invalide"); }
    Ok(url)
}

fn same_local_navigation(next: &Url, origin: &(String, String, Option<u16>)) -> bool {
    // WebKitGTK checks blob downloads as navigations. Accept only blobs
    // created by the same loopback origin as the Kiara page.
    let target = if next.scheme() == "blob" {
        Url::parse(next.path()).ok()
    } else {
        Some(next.clone())
    };
    target.is_some_and(|url| url.scheme() == origin.0
        && url.host_str() == Some(origin.1.as_str()) && url.port() == origin.2)
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

#[cfg(windows)]
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

#[cfg(windows)]
fn windows_startup_message(message: &str, hidden: bool) {
    #[link(name = "user32")]
    extern "system" {
        fn MessageBoxW(owner: *mut std::ffi::c_void, text: *const u16, title: *const u16, flags: u32) -> i32;
    }
    let message = match message {
        "Le profil Kiara est déjà ouvert" => "Kiara est déjà ouvert avec cet accès. Fermez la première fenêtre avant d’en ouvrir une autre.",
        "Le profil Kiara ne peut pas être protégé" => "Impossible de protéger les données locales. Réessayez après avoir vérifié votre session Windows.",
        "Le relais Kiara doit être mis à jour avant de continuer" => "Le client Kiara est incomplet. Réinstallez le paquet complet avant de continuer.",
        other => other,
    };
    eprintln!("{message}");
    if !hidden {
        let text: Vec<u16> = message.encode_utf16().chain([0]).collect();
        let title: Vec<u16> = "Kiara".encode_utf16().chain([0]).collect();
        unsafe { MessageBoxW(std::ptr::null_mut(), text.as_ptr(), title.as_ptr(), 0x30); }
    }
}

#[cfg(target_os = "linux")]
fn confirm_close(_window: &WebviewWindow) -> bool {
    use gtk::prelude::*;
    let dialog = gtk::MessageDialog::new(
        None::<&gtk::Window>, gtk::DialogFlags::MODAL, gtk::MessageType::Warning,
        gtk::ButtonsType::YesNo,
        "Des modifications peuvent être en attente. Fermer Kiara quand même ?",
    );
    dialog.set_title("Fermer Kiara");
    dialog.set_default_response(gtk::ResponseType::No);
    let confirmed = dialog.run() == gtk::ResponseType::Yes;
    dialog.close();
    confirmed
}

#[cfg(target_os = "linux")]
fn microphone_permission() -> tauri::webview::PermissionResponse {
    use gtk::prelude::*;
    use tauri::webview::PermissionResponse;
    let dialog = gtk::MessageDialog::new(
        None::<&gtk::Window>, gtk::DialogFlags::MODAL, gtk::MessageType::Question,
        gtk::ButtonsType::YesNo,
        "Autoriser Kiara à utiliser le microphone pour cette capture ?",
    );
    dialog.set_title("Accès au microphone");
    dialog.set_default_response(gtk::ResponseType::No);
    let allowed = dialog.run() == gtk::ResponseType::Yes;
    dialog.close();
    if allowed { PermissionResponse::Allow } else { PermissionResponse::Deny }
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

#[cfg(windows)]
fn relay_reply(input: &RelayInput, reply: u8) {
    if let Some(stream) = input.lock().unwrap().as_mut() {
        let _ = stream.write_all(&[reply]);
    }
}

#[cfg(windows)]
fn update_installer(line: &str) -> Option<(&Path, &str)> {
    let value = line.strip_suffix('\n')?.trim_end_matches('\r');
    let (digest, path) = value.strip_prefix("KIARA_RELAY_UPDATE ")?.split_once(' ')?;
    if digest.len() != 64 || !digest.bytes().all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase()) {
        return None;
    }
    let path = Path::new(path);
    let release = path.file_name()?.to_str()?.strip_prefix("Kiara_4.")?.strip_suffix("_x64-setup.exe")?;
    let (minor, patch) = release.split_once('.')?;
    if !path.is_absolute() || [minor, patch].iter().any(|part| {
        part.is_empty() || part.len() > 4 || !part.bytes().all(|byte| byte.is_ascii_digit())
    }) {
        return None;
    }
    Some((path, digest))
}

#[cfg(windows)]
fn verified_installer(root: &Path, installer: &Path, expected: &str) -> Option<(PathBuf, std::fs::File)> {
    use sha2::{Digest, Sha256};
    use std::{fs::OpenOptions, os::windows::fs::OpenOptionsExt};

    let stage = installer.parent()?;
    let stage_name = stage.file_name()?.to_str()?;
    if stage.parent()? != root || !stage_name.starts_with("kiara-update-") {
        return None;
    }
    let canonical_root = root.parent()?.canonicalize().ok()?.join(root.file_name()?);
    let canonical_stage = canonical_root.join(stage_name);
    let canonical_installer = canonical_stage.join(installer.file_name()?);
    if stage.canonicalize().ok()? != canonical_stage || installer.canonicalize().ok()? != canonical_installer {
        return None;
    }
    // Keep the verified file open without write or delete sharing until CreateProcess succeeds.
    let mut file = OpenOptions::new().read(true).share_mode(1).open(&canonical_installer).ok()?;
    if !file.metadata().ok()?.is_file() { return None; }
    let mut digest = Sha256::new();
    std::io::copy(&mut file, &mut digest).ok()?;
    if format!("{:x}", digest.finalize()) != expected { return None; }
    Some((canonical_installer, file))
}

#[cfg(windows)]
fn watch_updates(window: &WebviewWindow, pending: Arc<AtomicBool>, input: RelayInput, events: mpsc::Receiver<String>) {
    let window = window.clone();
    thread::spawn(move || {
        for event in events {
            let Some((installer, digest)) = update_installer(&event) else { continue; };
            if pending.swap(true, Ordering::AcqRel) {
                relay_reply(&input, b'c');
                continue;
            }
            if !wait_for_close_save(&window) {
                relay_reply(&input, b'c');
                pending.store(false, Ordering::Release);
                continue;
            }
            let verified = std::env::var_os("LOCALAPPDATA")
                .map(PathBuf::from).map(|base| base.join("QwenClient").join("desktop-updates"))
                .and_then(|root| verified_installer(&root, installer, digest));
            let Some((installer, verified_file)) = verified else {
                relay_reply(&input, b'c');
                pending.store(false, Ordering::Release);
                continue;
            };
            let handle = window.clone();
            let input_for_window = input.clone();
            let pending_for_window = pending.clone();
            if window.run_on_main_thread(move || {
                // The installer waits for this process and its relay to finish closing.
                let started = Command::new(&installer)
                    .args(["/P", "/UPDATE", "/R"])
                    .arg(format!("/KIARA-WAIT={}", std::process::id()))
                    .stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null())
                    .spawn().is_ok();
                drop(verified_file);
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

#[cfg(target_os = "linux")]
fn linux_data_home() -> Option<PathBuf> {
    std::env::var_os("XDG_DATA_HOME").map(PathBuf::from).filter(|path| path.is_absolute())
        .or_else(|| std::env::var_os("HOME").map(PathBuf::from).filter(|path| path.is_absolute()).map(|path| path.join(".local/share")))
}

#[cfg(target_os = "linux")]
#[derive(Debug, PartialEq, Eq)]
enum ProfileLockError { InUse, Unavailable, RelayOutdated }

#[cfg(target_os = "linux")]
fn lock_linux_profile(base: &Path, profile: Option<&str>) -> Result<std::fs::File, ProfileLockError> {
    use std::os::unix::fs::OpenOptionsExt;
    let directory = base.join("kiara");
    std::fs::create_dir_all(&directory).map_err(|_| ProfileLockError::Unavailable)?;
    let name = profile.map(|value| format!("tauri-{value}.lock")).unwrap_or_else(|| "tauri-default.lock".into());
    let file = std::fs::OpenOptions::new().read(true).write(true).create(true).mode(0o600)
        .open(directory.join(name)).map_err(|_| ProfileLockError::Unavailable)?;
    match file.try_lock() {
        Ok(()) => Ok(file),
        Err(std::fs::TryLockError::WouldBlock) => Err(ProfileLockError::InUse),
        Err(std::fs::TryLockError::Error(_)) => Err(ProfileLockError::Unavailable),
    }
}

#[cfg(target_os = "linux")]
fn profile_lock_message(error: ProfileLockError, hidden: bool) {
    let message = match error {
        ProfileLockError::InUse => "Kiara est déjà ouvert avec cet accès. Fermez la première fenêtre avant d’en ouvrir une autre.",
        ProfileLockError::Unavailable => "Impossible de protéger les données locales. Vérifiez l’accès au dossier Kiara, puis réessayez.",
        ProfileLockError::RelayOutdated => "Le client Kiara est incomplet. Réinstallez le paquet Linux complet avant de continuer.",
    };
    linux_startup_message(message, hidden);
}

#[cfg(target_os = "linux")]
fn linux_startup_message(message: &str, hidden: bool) {
    use gtk::prelude::*;
    eprintln!("{message}");
    if !hidden && gtk::init().is_ok() {
        let dialog = gtk::MessageDialog::new(None::<&gtk::Window>, gtk::DialogFlags::MODAL,
            gtk::MessageType::Warning, gtk::ButtonsType::Ok, message);
        dialog.set_title("Kiara");
        dialog.run();
        dialog.close();
    }
}

fn recovery_profile_directory(identity: &str) -> Option<PathBuf> {
    #[cfg(windows)]
    { std::env::var_os("LOCALAPPDATA").map(PathBuf::from)
        .map(|base| base.join("QwenClient").join(format!("webview-{identity}"))) }
    #[cfg(target_os = "linux")]
    { linux_data_home().map(|base| base.join("kiara").join(format!("tauri-webview-{identity}"))) }
}

fn recovery_error(message: &str, hidden: bool) {
    #[cfg(windows)]
    windows_startup_message(message, hidden);
    #[cfg(target_os = "linux")]
    linux_startup_message(message, hidden);
}

fn open_main_window(app: &tauri::AppHandle, url: Url, directory: Option<PathBuf>, hidden: bool,
                    updates: Option<(RelayInput, mpsc::Receiver<String>)>) -> tauri::Result<()> {
    #[cfg(target_os = "linux")]
    use tauri::Manager;
    #[cfg(target_os = "linux")]
    {
        use tauri::ipc::CapabilityBuilder;
        app.add_capability(CapabilityBuilder::new("kiara-zoom").local(false)
            .remote(format!("http://127.0.0.1:{}/*", url.port().unwrap())).window("main")
            .permission("core:webview:allow-set-webview-zoom"))?;
    }
    let (width, height) = app.primary_monitor().ok().flatten()
        .map(|monitor| initial_window_size(monitor.work_area().size.width,
                                          monitor.work_area().size.height, monitor.scale_factor()))
        .unwrap_or((1100.0, 650.0));
    let origin = (url.scheme().to_owned(), url.host_str().unwrap().to_owned(), url.port());
    #[allow(unused_mut)]
    let mut builder = WebviewWindowBuilder::new(app, "main", WebviewUrl::External(url))
        .title("Kiara").zoom_hotkeys_enabled(true).visible(!hidden)
        .inner_size(width, height).min_inner_size(width.min(600.0), height.min(450.0))
        .on_navigation(move |next| same_local_navigation(&next, &origin));
    if let Some(directory) = directory { builder = builder.data_directory(directory); }
    #[cfg(target_os = "linux")]
    {
        use tauri::webview::{PermissionKind, PermissionResponse};
        builder = builder.initialization_script(include_str!("linux_zoom_keys.js"));
        builder = builder.on_permission_request(|_, kind| match kind {
            PermissionKind::Microphone => microphone_permission(),
            PermissionKind::Camera => PermissionResponse::Deny,
            _ => PermissionResponse::Default,
        });
    }
    let window = builder.build()?;
    if let Some((input, events)) = updates {
        let pending = Arc::new(AtomicBool::new(false));
        protect_close(&window, pending.clone());
        #[cfg(windows)]
        watch_updates(&window, pending, input, events);
        #[cfg(target_os = "linux")]
        let _ = (pending, input, events);
    }
    Ok(())
}

fn run_recovery(context: tauri::Context<tauri::Wry>, offer: recovery_protocol::RecoveryOffer,
                relay: Relay, events: mpsc::Receiver<String>, hidden: bool) {
    use tauri::Manager;
    let identity = offer.identity().to_owned();
    let Some(directory) = recovery_profile_directory(&identity) else {
        recovery_error("Impossible de retrouver le dossier du profil Kiara.", hidden);
        std::process::exit(2);
    };
    let input = relay.1.clone();
    let result = tauri::Builder::default().setup(move |app| {
        let handle = app.handle().clone();
        let recovery = recovery_window::build(&handle, &offer, directory.clone(), hidden)?;
        let cancel_handle = handle.clone();
        recovery.on_window_event(move |event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                // Hidden transfer windows must not keep a cancelled recovery alive.
                api.prevent_close();
                cancel_handle.exit(0);
            }
        });
        thread::spawn(move || {
            let mut transfer_active = false;
            let mut review_shown = false;
            loop {
                let line = match events.recv() {
                    Ok(line) => line,
                    Err(_) => {
                        let callback = handle.clone();
                        let _ = handle.run_on_main_thread(move || {
                            recovery_error("Le relais Kiara ne répond plus.", hidden);
                            callback.exit(2);
                        });
                        return;
                    }
                };
                if line.starts_with("KIARA_RELAY_ORIGIN_TRANSFER ") {
                    let offer = recovery_protocol::parse_transfer_offer(&line);
                    if transfer_active || offer.as_ref().map(|value| value.identity()) != Some(identity.as_str()) {
                        let callback = handle.clone();
                        let _ = handle.run_on_main_thread(move || { recovery_error("Transfert local invalide.", hidden); callback.exit(2); });
                        return;
                    }
                    let offer = offer.expect("checked transfer offer");
                    let callback = handle.clone();
                    let data_directory = directory.clone();
                    let (done, confirmation) = mpsc::sync_channel(1);
                    if handle.run_on_main_thread(move || {
                        let ok = callback.get_webview_window("origin-recovery").is_some()
                            && callback.get_webview_window("origin-transfer-source").is_none()
                            && callback.get_webview_window("origin-transfer-destination").is_none()
                            && recovery_window::build_transfer(&callback, &offer, data_directory).is_ok();
                        let _ = done.send(ok);
                    }).is_err() || !matches!(confirmation.recv_timeout(Duration::from_secs(15)), Ok(true)) {
                        let callback = handle.clone();
                        let _ = handle.run_on_main_thread(move || { recovery_error("Impossible d’ouvrir les fenêtres de récupération.", hidden); callback.exit(2); });
                        return;
                    }
                    transfer_active = true;
                    review_shown = false;
                    continue;
                }
                if line.trim_end() == "KIARA_RELAY_ORIGIN_REVIEW" {
                    if !transfer_active || review_shown {
                        let callback = handle.clone();
                        let _ = handle.run_on_main_thread(move || { recovery_error("Comparaison des versions indisponible.", hidden); callback.exit(2); });
                        return;
                    }
                    let callback = handle.clone();
                    let (done, confirmation) = mpsc::sync_channel(1);
                    if handle.run_on_main_thread(move || {
                        let ok = callback.get_webview_window("origin-transfer-destination").map(|window| {
                            let cancel = callback.clone();
                            window.on_window_event(move |event| {
                                if let WindowEvent::CloseRequested { api, .. } = event {
                                    api.prevent_close();
                                    cancel.exit(0);
                                }
                            });
                            let shown = window.show().is_ok();
                            if shown { let _ = window.set_focus(); }
                            shown
                        }).unwrap_or(false);
                        let _ = done.send(ok);
                    }).is_err() || !matches!(confirmation.recv_timeout(Duration::from_secs(15)), Ok(true)) {
                        let callback = handle.clone();
                        let _ = handle.run_on_main_thread(move || { recovery_error("Impossible d’ouvrir la comparaison des versions.", hidden); callback.exit(2); });
                        return;
                    }
                    let acknowledged = input.lock().ok().and_then(|mut guard| {
                        guard.as_mut().map(|stream| stream.write_all(b"K").and_then(|_| stream.flush()).is_ok())
                    }).unwrap_or(false);
                    if !acknowledged {
                        let callback = handle.clone();
                        let _ = handle.run_on_main_thread(move || { recovery_error("Le relais ne confirme plus la récupération.", hidden); callback.exit(2); });
                        return;
                    }
                    review_shown = true;
                    continue;
                }
                if line.trim_end() == "KIARA_RELAY_ORIGIN_TRANSFER_DONE" {
                    if !transfer_active {
                        let callback = handle.clone();
                        let _ = handle.run_on_main_thread(move || { recovery_error("Fermeture de récupération invalide.", hidden); callback.exit(2); });
                        return;
                    }
                    let callback = handle.clone();
                    let (done, confirmation) = mpsc::sync_channel(1);
                    if handle.run_on_main_thread(move || {
                        let mut ok = callback.get_webview_window("origin-transfer-destination").is_some();
                        for label in ["origin-transfer-source", "origin-transfer-destination"] {
                            if let Some(window) = callback.get_webview_window(label) {
                                ok &= window.destroy().is_ok();
                            }
                        }
                        let _ = done.send(ok);
                    }).is_err() || !matches!(confirmation.recv_timeout(Duration::from_secs(15)), Ok(true)) {
                        let callback = handle.clone();
                        let _ = handle.run_on_main_thread(move || { recovery_error("Impossible de fermer les fenêtres de récupération.", hidden); callback.exit(2); });
                        return;
                    }
                    let acknowledged = input.lock().ok().and_then(|mut guard| {
                        guard.as_mut().map(|stream| stream.write_all(b"K").and_then(|_| stream.flush()).is_ok())
                    }).unwrap_or(false);
                    if !acknowledged {
                        let callback = handle.clone();
                        let _ = handle.run_on_main_thread(move || { recovery_error("Le relais ne confirme plus la récupération.", hidden); callback.exit(2); });
                        return;
                    }
                    transfer_active = false;
                    continue;
                }
                let ready = if transfer_active { Err("Transfert local non terminé") } else {
                    relay_ready(&line).and_then(|(url, found)| if found == identity { Ok(url) }
                        else { Err("Identifiant de profil Kiara invalide") })
                };
                let callback = handle.clone();
                let _ = handle.run_on_main_thread(move || {
                    if callback.get_webview_window("origin-recovery").is_none() { return; }
                    match ready {
                        Ok(url) => {
                            if open_main_window(&callback, url, Some(directory), hidden, Some((input, events))).is_ok() {
                                let _ = recovery.destroy();
                            } else {
                                recovery_error("Impossible d’ouvrir la fenêtre principale de Kiara.", hidden);
                                callback.exit(2);
                            }
                        }
                        Err(message) => { recovery_error(message, hidden); callback.exit(2); }
                    }
                });
                return;
            }
        });
        Ok(())
    }).build(context);
    let exit_code = match result {
        Ok(app) => app.run_return(|_, _| {}),
        Err(_) => { recovery_error("Impossible d’ouvrir la vérification des données locales.", hidden); 2 }
    };
    drop(relay);
    std::process::exit(exit_code);
}

fn main() {
    let context = tauri::generate_context!();
    #[cfg(target_os = "linux")]
    {
        // Keep the version marker in the executable for cross-platform packaging.
        let marker = std::hint::black_box(concat!("KIARA_TAURI_VERSION=", env!("KIARA_LINUX_BUILD_VERSION"), "\0"));
        let version = marker.strip_prefix("KIARA_TAURI_VERSION=").and_then(|value| value.strip_suffix('\0'));
        if version != Some(context.package_info().version.to_string().as_str()) {
            eprintln!("La version du binaire Kiara ne correspond pas à sa configuration Tauri.");
            std::process::exit(2);
        }
    }
    let args: Vec<_> = std::env::args_os().collect();
    let mut relay = None;
    let mut updates = None;
    let mut profile_directory = None;
    let (url, hidden) = match args.as_slice() {
        [_, flag, value] if flag == "--local-url" => (diagnostic_url(&value.to_string_lossy()), false),
        [_, flag, value, hidden] if flag == "--local-url" && hidden == "--hidden" => {
            (diagnostic_url(&value.to_string_lossy()), true)
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
                Ok(Some(RelayStart::Ready(url, identity, child, events))) => {
                    updates = Some((child.1.clone(), events));
                    relay = Some(child);
                    profile_directory = recovery_profile_directory(&identity);
                    (Ok(url), hidden)
                }
                Ok(Some(RelayStart::Recovery(offer, child, events))) => {
                    run_recovery(context, offer, child, events, hidden);
                    return;
                }
                Ok(None) => return,
                Err(message) => (Err(message), hidden),
            }
        }
    };
    let url = match url {
        Ok(url) => url,
        Err(message) => {
            #[cfg(target_os = "linux")]
            if message == "Le profil Kiara est déjà ouvert" {
                profile_lock_message(ProfileLockError::InUse, hidden);
            } else if message == "Le profil Kiara ne peut pas être protégé" {
                profile_lock_message(ProfileLockError::Unavailable, hidden);
            } else if message == "Le relais Kiara doit être mis à jour avant de continuer" {
                profile_lock_message(ProfileLockError::RelayOutdated, hidden);
            } else {
                linux_startup_message(message, hidden);
            }
            #[cfg(windows)]
            windows_startup_message(message, hidden);
            std::process::exit(2);
        }
    };
    #[cfg(target_os = "linux")]
    let _profile_guard = if profile_directory.is_none() {
        Some(match linux_data_home().ok_or(ProfileLockError::Unavailable)
            .and_then(|base| lock_linux_profile(&base, None)) {
            Ok(guard) => guard,
            Err(error) => {
                drop(relay);
                profile_lock_message(error, hidden);
                std::process::exit(3);
            }
        })
    } else {None}; // Normal Linux relays hold the same profile lock before loading data.
    let app = tauri::Builder::default()
        .setup(move |app| {
            open_main_window(app.handle(), url, profile_directory, hidden, updates)?;
            Ok(())
        })
        .build(context)
        .expect("Impossible de démarrer Kiara");
    let exit_code = app.run_return(|_, _| {});
    drop(relay);
    std::process::exit(exit_code);
}

fn initial_window_size(width: u32, height: u32, scale: f64) -> (f64, f64) {
    let scale = if scale.is_finite() && scale > 0.0 { scale } else { 1.0 };
    ((f64::from(width) / scale * 0.9).clamp(240.0, 1280.0),
     (f64::from(height) / scale * 0.9).clamp(200.0, 800.0))
}

#[cfg(test)]
mod tests {
    use super::{initial_window_size, local_url, relay_ready, same_local_navigation};
    #[cfg(windows)]
    use super::update_installer;

    #[test]
    fn window_fits_work_area_from_720p_through_wqhd() {
        let (width, height) = initial_window_size(1280, 672, 1.0);
        assert!((width - 1152.0).abs() < 0.01 && (height - 604.8).abs() < 0.01);
        assert_eq!(initial_window_size(2560, 1400, 1.0), (1280.0, 800.0));
        let (width, height) = initial_window_size(1280, 672, 1.5);
        assert!(width * 1.5 < 1280.0 && height * 1.5 < 672.0);
    }

    #[test]
    fn navigation_accepts_only_the_local_origin_and_its_blobs() {
        let origin = ("http".to_string(), "127.0.0.1".to_string(), Some(17843));
        for value in ["http://127.0.0.1:17843/chat", "blob:http://127.0.0.1:17843/fiction"] {
            assert!(same_local_navigation(&super::Url::parse(value).unwrap(), &origin), "{value}");
        }
        for value in ["http://127.0.0.1:17844/chat", "https://127.0.0.1:17843/chat",
                      "blob:http://127.0.0.1:17844/fiction", "blob:https://127.0.0.1:17843/fiction",
                      "blob:http://example.test:17843/fiction", "blob:null/fiction", "file:///tmp/fiction"] {
            assert!(!same_local_navigation(&super::Url::parse(value).unwrap(), &origin), "{value}");
        }
    }

    #[test]
    #[cfg(windows)]
    fn only_accepts_a_windows_installer_from_the_relay() {
        let sha = "a".repeat(64);
        assert!(update_installer(&format!("KIARA_RELAY_UPDATE {sha} C:\\Usér Files\\Kiara_4.0.2_x64-setup.exe\r\n")).is_some());
        assert!(update_installer(&format!("KIARA_RELAY_UPDATE {sha} C:\\Kiara_3.5.63_x64-setup.exe\n")).is_none());
        assert!(update_installer(&format!("KIARA_RELAY_UPDATE {sha} Kiara_4.0.2_x64-setup.exe\n")).is_none());
        assert!(update_installer("KIARA_RELAY_UPDATE C:\\Kiara_4.0.2_x64-setup.exe\n").is_none());
    }

    #[test]
    #[cfg(windows)]
    fn staged_installer_requires_the_expected_directory_and_digest() {
        use sha2::{Digest, Sha256};
        use std::{fs, time::{SystemTime, UNIX_EPOCH}};

        let identity = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos();
        let root = std::env::temp_dir().join(format!("kiara-update-test-{identity}"));
        let stage = root.join("kiara-update-fixture");
        fs::create_dir_all(&stage).unwrap();
        let installer = stage.join("Kiara_4.0.22_x64-setup.exe");
        let bytes = b"isolated installer fixture";
        fs::write(&installer, bytes).unwrap();
        let digest = format!("{:x}", Sha256::digest(bytes));
        assert!(super::verified_installer(&root, &installer, &digest).is_some());
        assert!(super::verified_installer(&root, &installer, &"0".repeat(64)).is_none());
        assert!(super::verified_installer(&root.join("other"), &installer, &digest).is_none());
        fs::remove_file(installer).unwrap();
        fs::remove_dir(stage).unwrap();
        fs::remove_dir(root).unwrap();
    }

    #[test]
    fn recovery_receiver_error_explains_safe_retry_without_assuming_port_conflict() {
        let message = relay_ready("KIARA_RELAY_RECEIVER_UNAVAILABLE\n").unwrap_err();
        assert!(message.contains("données restent sur cet appareil"));
        assert!(message.contains("Relancez Kiara"));
        assert!(!message.contains("port"));
        assert!(relay_ready("KIARA_RELAY_RECOVERY_UNAVAILABLE\n").unwrap_err().contains("port"));
    }

    #[test]
    fn relay_supplies_a_local_origin_and_safe_profile_directory_key() {
        let ready = format!("KIARA_RELAY_READY http://127.0.0.1:45678/chat?launch={} 0123456789abcdef0123", "a".repeat(64));
        let (url, key) = relay_ready(&ready).unwrap();
        assert_eq!(url.port(), Some(45678));
        assert_eq!(key, "0123456789abcdef0123");
        assert_eq!(relay_ready(&format!("{ready}\r\n")).unwrap().1, key);
        assert!(relay_ready("KIARA_RELAY_READY http://127.0.0.1:45678/chat 0123456789abcdef0123").is_err());
        assert!(relay_ready("KIARA_RELAY_READY http://127.0.0.1:45678/chat ../another-profile").is_err());
        assert!(relay_ready("KIARA_RELAY_ORIGIN_BUSY\n").unwrap_err().contains("occupé"));
        assert!(relay_ready("KIARA_RELAY_ORIGIN_MULTIPLE\n").unwrap_err().contains("conservées"));
        assert!(relay_ready("KIARA_RELAY_ORIGIN_INVALID\n").unwrap_err().contains("vérifier"));
        assert!(relay_ready("KIARA_RELAY_SETTINGS_UNREADABLE\n").unwrap_err().contains("original est conservé"));
        assert!(relay_ready("KIARA_RELAY_ARCHIVE_UNAVAILABLE\n").unwrap_err().contains("sauvegarde"));
        assert!(relay_ready("KIARA_RELAY_QT_STORAGE\n").unwrap_err().contains("conservées"));
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn linux_profile_lock_excludes_only_the_same_profile_and_releases_on_close() {
        use super::{lock_linux_profile, ProfileLockError};
        let root = std::env::temp_dir().join(format!("kiara-profile-lock-{}-{}", std::process::id(),
            std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()));
        let first = lock_linux_profile(&root, Some("webview-a")).unwrap();
        assert_eq!(lock_linux_profile(&root, Some("webview-a")).unwrap_err(), ProfileLockError::InUse);
        let other = lock_linux_profile(&root, Some("webview-b")).unwrap();
        drop(first);
        let reopened = lock_linux_profile(&root, Some("webview-a")).unwrap();
        drop((other,reopened));
        std::fs::remove_file(root.join("kiara/tauri-webview-a.lock")).unwrap();
        std::fs::remove_file(root.join("kiara/tauri-webview-b.lock")).unwrap();
        std::fs::remove_dir(root.join("kiara")).unwrap();
        std::fs::remove_dir(root).unwrap();
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
