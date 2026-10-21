"""Keep Windows loopback administration inside its owning Windows account.

Host/Origin and the page token still handle browser requests. Windows' TCP owner
table supplies the peer PID; HTTP headers cannot choose the accepted identity.
"""
import os

import psutil

from http_boundary import BoundedHTTPServer


def same_windows_user(connection, *, owner, connections=None, process=psutil.Process):
    """Fail closed when the outbound loopback socket or its account is unknown."""
    try:
        local = connection.getsockname()
        peer = connection.getpeername()
        if local[0] != '127.0.0.1' or peer[0] != '127.0.0.1':
            return False
        rows = psutil.net_connections(kind='tcp') if connections is None else connections
        for row in rows:
            if (row.pid and row.laddr and row.raddr
                    and tuple(row.laddr) == peer and tuple(row.raddr) == local
                    and row.status == psutil.CONN_ESTABLISHED):
                return process(row.pid).username().casefold() == owner.casefold()
    except (OSError, psutil.Error):
        pass
    return False


class LocalUserHTTPServer(BoundedHTTPServer):
    def __init__(self, *args, **kwargs):
        self.windows_owner = psutil.Process().username() if os.name == 'nt' else None
        super().__init__(*args, **kwargs)

    def verify_request(self, request, address):
        if self.windows_owner is None or same_windows_user(request, owner=self.windows_owner):
            return True
        try:
            request.sendall(b'HTTP/1.0 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n')
        except OSError:
            pass
        return False
