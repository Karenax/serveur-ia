//! Parser for a future private recovery offer from the profile-locked relay.
//! The token is deliberately not printable or written to logs.

pub struct RecoveryOffer {
    identity: String,
    token: String,
}

impl RecoveryOffer {
    pub fn identity(&self) -> &str { &self.identity }
    pub fn token(&self) -> &str { &self.token }
}

pub fn parse_recovery_offer(line: &str) -> Option<RecoveryOffer> {
    let text = line.strip_suffix('\n')?;
    let text = text.strip_suffix('\r').unwrap_or(text);
    let (identity, token) = text.strip_prefix("KIARA_RELAY_ORIGIN_SCAN ")?.split_once(' ')?;
    let lowercase_hex = |value: &str| value.bytes().all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte));
    if identity.len() != 20 || token.len() != 64 || !lowercase_hex(identity) || !lowercase_hex(token) {
        return None;
    }
    Some(RecoveryOffer { identity: identity.to_owned(), token: token.to_owned() })
}

/// Private transfer instruction; never print the token or profile identity.
pub struct TransferOffer {
    identity: String,
    token: String,
    source: u16,
    destination: u16,
    qt_source: bool,
    snapshot: bool,
    manifest: bool,
}

impl TransferOffer {
    pub fn identity(&self) -> &str { &self.identity }
    pub fn token(&self) -> &str { &self.token }
    pub fn source(&self) -> u16 { self.source }
    pub fn destination(&self) -> u16 { self.destination }
    pub fn qt_source(&self) -> bool { self.qt_source }
    pub fn snapshot(&self) -> bool { self.snapshot }
    pub fn manifest(&self) -> bool { self.manifest }
}

pub fn parse_transfer_offer(line: &str) -> Option<TransferOffer> {
    let text = line.strip_suffix('\n')?;
    let text = text.strip_suffix('\r').unwrap_or(text);
    let mut parts = text.strip_prefix("KIARA_RELAY_ORIGIN_TRANSFER ")?.split(' ');
    let identity = parts.next()?;
    let token = parts.next()?;
    let source_text = parts.next()?;
    let destination_text = parts.next()?;
    let kind = parts.next()?;
    let mode = parts.next()?;
    if parts.next().is_some() { return None; }
    let lowercase_hex = |value: &str| value.bytes().all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte));
    if identity.len() != 20 || token.len() != 64 || !lowercase_hex(identity) || !lowercase_hex(token) {
        return None;
    }
    let source: u16 = source_text.parse().ok()?;
    let destination: u16 = destination_text.parse().ok()?;
    let ports = crate::recovery_policy::RecoveryOrigins::standard();
    if source.to_string() != source_text || destination.to_string() != destination_text
        || !ports.ports().contains(&source) || !ports.ports().contains(&destination) {
        return None;
    }
    let qt_source = match kind { "qt" => true, "tauri" => false, _ => return None };
    let (snapshot, manifest) = match mode { "snapshot" => (true,false), "transfer" => (false,false), "manifest" => (false,true), _ => return None };
    if (manifest && (qt_source || source != destination)) || (!manifest && !qt_source && source == destination) { return None; }
    Some(TransferOffer { identity: identity.to_owned(), token: token.to_owned(), source, destination, qt_source, snapshot, manifest })
}

#[cfg(test)]
mod tests {
    use super::{parse_recovery_offer, parse_transfer_offer};

    #[test]
    fn accepts_only_a_complete_bounded_offer() {
        let identity = "a".repeat(20);
        let token = "b".repeat(64);
        let valid = format!("KIARA_RELAY_ORIGIN_SCAN {identity} {token}\n");
        let offer = parse_recovery_offer(&valid).unwrap();
        assert_eq!(offer.identity, identity);
        assert_eq!(offer.token, token);
        assert!(parse_recovery_offer(&valid.replace('\n', "\r\n")).is_some());
        for bad in [valid.trim_end().to_owned(), valid.replace('a', "A"),
                    valid.replace("ORIGIN_SCAN", "ORIGIN_OTHER"), format!("{valid}extra"),
                    format!("KIARA_RELAY_ORIGIN_SCAN {} {}\n", "a".repeat(19), "b".repeat(64)),
                    format!("KIARA_RELAY_ORIGIN_SCAN {} {}\n", "a".repeat(20), "b".repeat(65))] {
            assert!(parse_recovery_offer(&bad).is_none());
        }
    }

    #[test]
    fn transfer_offer_validates_identity_token_ports_and_engine() {
        let prefix = format!("KIARA_RELAY_ORIGIN_TRANSFER {} {}", "a".repeat(20), "b".repeat(64));
        let valid = format!("{prefix} 17842 17841 tauri transfer\n");
        let offer = parse_transfer_offer(&valid).unwrap();
        assert_eq!((offer.identity(), offer.token(), offer.source(), offer.destination(), offer.qt_source()),
                   ("aaaaaaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", 17842, 17841, false));
        let qt = parse_transfer_offer(&format!("{prefix} 17841 17841 qt snapshot\r\n")).unwrap();
        assert!(qt.qt_source() && qt.snapshot());
        let manifest = parse_transfer_offer(&format!("{prefix} 17841 17841 tauri manifest\n")).unwrap();
        assert!(manifest.manifest() && !manifest.snapshot() && !manifest.qt_source());
        assert!(parse_transfer_offer(&format!("{prefix} 17842 17841 tauri manifest\n")).is_none());
        assert!(parse_transfer_offer(&format!("{prefix} 17841 17841 qt manifest\n")).is_none());
        for invalid in [valid.trim_end().to_owned(), valid.replace("17842", "017842"),
                        valid.replace("17842", "17840"), valid.replace("17841", "17851"),
                        valid.replace("17842", "17841"), valid.replace("tauri", "other"), valid.replace("transfer", "other"),
                        valid.replace('a', "A"), format!("{valid}extra")] {
            assert!(parse_transfer_offer(&invalid).is_none());
        }
    }
}
