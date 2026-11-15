"""Opt-in effective Python socket restriction for the isolated qualification.

This guards Python audit events, not OS networking or native-library syscalls.
Loopback remains available for the local LM Studio model.
"""
import os
import socket
import sys

_installed = False
_denied = 0


def install():
    global _installed
    if _installed or os.environ.get("AGENT_QUALIFICATION_OFFLINE") != "1":
        return

    def audit(event, args):
        global _denied
        if event in {"socket.connect", "socket.getaddrinfo"}:
            address = args[1] if event == "socket.connect" else args[0]
            host = address[0] if isinstance(address, tuple) else address
            if host not in {"127.0.0.1", "::1", "localhost", None}:
                _denied += 1
                raise PermissionError("Connexion externe interdite pendant qualification hors réseau")

    sys.addaudithook(audit)
    _installed = True


def verify():
    install()
    blocked = False
    if _installed:
        with socket.socket() as probe:
            try:
                probe.connect(("192.0.2.1", 9))  # TEST-NET, never sent past audit hook
            except PermissionError:
                blocked = True
    return {"enabled": _installed, "probe_blocked": blocked,
            "denied_attempts": _denied, "scope": "Python sockets; native syscalls not covered"}
