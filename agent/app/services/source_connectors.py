"""Explicit selected-source fetches, pinned public DNS and retained calendar context."""
import hashlib
import http.client
import ipaddress
import socket
import ssl
from urllib.parse import urlsplit, quote

from fastapi import HTTPException

from .source_library import MAX_FILE


def public_url(url):
    parts = urlsplit(url)
    if (parts.scheme not in {"https", "http"} or not parts.hostname or parts.username or parts.password
            or any(ord(c) < 32 for c in url) or len(url) > 2048):
        raise HTTPException(422, "Adresse HTTP(S) publique sans identifiants requise")
    try:
        port = parts.port or (443 if parts.scheme == "https" else 80)
        addresses = socket.getaddrinfo(parts.hostname, port, type=socket.SOCK_STREAM)
    except (ValueError, OSError) as exc:
        raise HTTPException(422, "Adresse source introuvable") from exc
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise HTTPException(422, "Adresse source publique requise")
    return parts, port, addresses[0][4][0]


def fetch_selected(url, *, bearer=None):
    parts, port, address = public_url(url)
    # Connect to the address already checked; DNS cannot rebound to a private host.
    sock = socket.create_connection((address, port), timeout=20)
    if parts.scheme == "https":
        sock = ssl.create_default_context().wrap_socket(sock, server_hostname=parts.hostname)
    connection = http.client.HTTPConnection(parts.hostname, port, timeout=20)
    connection.sock = sock
    host = parts.hostname if port in {80, 443} else f"{parts.hostname}:{port}"
    headers = {"Host": host, "User-Agent": "Agent-Selected-Source/1.0", "Accept-Encoding": "identity"}
    if bearer:
        if parts.scheme != "https" or parts.hostname != "www.googleapis.com":
            connection.close()
            raise HTTPException(422, "Jeton réservé à Google Drive HTTPS")
        headers["Authorization"] = "Bearer " + bearer
    path = quote(parts.path or "/", safe="/%:@!$&'()*+,;=-._~")
    if parts.query:
        path += "?" + parts.query
    try:
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        if response.status != 200:
            raise HTTPException(502, f"Source distante : réponse HTTP {response.status}")
        if response.getheader("Content-Encoding", "identity") != "identity":
            raise HTTPException(422, "Encodage distant compressé non accepté")
        data = response.read(MAX_FILE + 1)
        if len(data) > MAX_FILE:
            raise HTTPException(413, "Source distante supérieure à 50 Mio")
        return data, response.getheader("Content-Type", "application/octet-stream").split(";")[0]
    finally:
        connection.close()


def calendar_preview(data):
    if not data or len(data) > 1024 * 1024:
        raise HTTPException(413, "Calendrier limité à 1 Mio")
    try:
        raw = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(422, "Calendrier iCalendar UTF-8 requis") from exc
    if "BEGIN:VCALENDAR" not in raw:
        raise HTTPException(422, "Format iCalendar requis")
    lines = []
    for line in raw.replace("\r\n", "\n").split("\n"):
        if line.startswith((" ", "\t")) and lines:
            lines[-1] += line[1:]
        else:
            lines.append(line)
    events, current = [], None
    for line in lines:
        if line == "BEGIN:VEVENT":
            current = {"attendees": []}
        elif line == "END:VEVENT" and current is not None:
            if current.get("uid"):
                events.append(current)
            current = None
            if len(events) > 1000:
                raise HTTPException(413, "Calendrier limité à 1000 événements")
        elif current is not None and ":" in line:
            key, value = line.split(":", 1)
            name, *parameters = key.split(";")
            value = value.replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";")
            if name in {"UID", "SUMMARY", "DESCRIPTION", "LOCATION", "DTSTART", "DTEND"}:
                current[name.lower()] = value[:12000]
                if name in {"DTSTART", "DTEND"}:
                    current[name.lower() + "_parameters"] = parameters
            elif name == "ATTENDEE" and len(current["attendees"]) < 100:
                current["attendees"].append({"value": value, "parameters": parameters})
    return {"sha256": hashlib.sha256(data).hexdigest(), "events": events,
            "context_only": True, "dates_are_imported_metadata": True}
