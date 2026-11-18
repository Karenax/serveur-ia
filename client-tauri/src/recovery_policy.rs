//! Navigation boundary for the future, short-lived recovery window.
//!
//! The normal Kiara window keeps its existing single-origin boundary. The
//! recovery caller must first reserve every port and inject its private token
//! into the isolated window; this policy alone is not an authorization check.
use tauri::Url;

#[derive(Clone, Debug)]
pub struct RecoveryOrigins(Vec<u16>);

impl RecoveryOrigins {
    pub fn new(ports: Vec<u16>) -> Option<Self> {
        if ports.len() != 10 || ports.iter().any(|port| *port < 1024) {
            return None;
        }
        let mut sorted = ports.clone();
        sorted.sort_unstable();
        sorted.dedup();
        if sorted.len() != ports.len() { return None; }
        Some(Self(ports))
    }

    pub fn standard() -> Self {
        Self::new((17841..=17850).collect()).expect("static recovery ports")
    }

    pub fn ports(&self) -> &[u16] { &self.0 }

    pub fn allows(&self, url: &Url) -> bool {
        url.scheme() == "http"
            && url.host_str() == Some("127.0.0.1")
            && url.username().is_empty()
            && url.password().is_none()
            && url.port().is_some_and(|port| self.0.contains(&port))
            && matches!(url.path(), "/recovery" | "/recovery/scan" | "/recovery/transfer")
            && url.query().is_none()
            && url.fragment().is_none()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn permits_only_the_reserved_recovery_pages() {
        let policy = RecoveryOrigins::standard();
        for port in 17841..=17850 {
            assert!(policy.allows(&Url::parse(&format!("http://127.0.0.1:{port}/recovery")).unwrap()));
            assert!(policy.allows(&Url::parse(&format!("http://127.0.0.1:{port}/recovery/scan")).unwrap()));
            assert!(policy.allows(&Url::parse(&format!("http://127.0.0.1:{port}/recovery/transfer")).unwrap()));
        }
        for text in ["http://127.0.0.1:17840/recovery", "http://127.0.0.1:17851/recovery",
                     "http://localhost:17841/recovery", "https://127.0.0.1:17841/recovery",
                     "http://127.0.0.1:17841/chat", "http://127.0.0.1:17841/recovery/",
                     "http://127.0.0.1:17841/recovery?x=1", "http://127.0.0.1:17841/recovery#secret",
                     "http://user@127.0.0.1:17841/recovery", "http://127.0.0.1.evil.test:17841/recovery"] {
            assert!(!policy.allows(&Url::parse(text).unwrap()), "{text}");
        }
    }

    #[test]
    fn rejects_missing_duplicate_or_privileged_ports() {
        assert!(RecoveryOrigins::new(vec![17841; 10]).is_none());
        assert!(RecoveryOrigins::new(vec![17841; 9]).is_none());
        assert!(RecoveryOrigins::new((1..=10).collect()).is_none());
        assert!(RecoveryOrigins::new((20000..20010).collect()).is_some());
    }
}
