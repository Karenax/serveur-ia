"""Single reader for desktop cancellation, inventory and update commands.

The owner remains responsible for the stream. Transfer-specific commands are
used only by the experimental recovery prototype.
"""
from queue import Empty, Full, Queue
from io import BufferedReader
from threading import Event, Thread
from math import isfinite
from time import monotonic


class RelayControlStream:
    """Own an unread command stream through recovery and later updates."""

    def __init__(self, stream, *, capacity=16):
        if not hasattr(stream, 'read') or type(capacity) is not int or capacity < 1:
            raise ValueError('Canal du client invalide.')
        self._stream = stream
        # This is the sole reader, before anything has been buffered. Reading
        # the raw pipe avoids holding BufferedReader's lock while the desktop
        # closes during recovery, which can delay frozen Windows shutdown.
        self._reader_stream = stream.raw if isinstance(stream, BufferedReader) else stream
        self._pending = Queue(maxsize=capacity)
        self._closed = Event()
        self._reader = Thread(target=self._receive, daemon=True)
        self._reader.start()

    def _receive(self):
        try:
            while True:
                command = self._reader_stream.read(1)
                if not command:
                    return
                if not isinstance(command, bytes) or len(command) != 1:
                    return
                try:self._pending.put_nowait(command)
                except Full:return
        except (OSError, ValueError):
            pass
        finally:
            self._closed.set()

    def cancelled(self):
        return self._closed.is_set()

    def wait_recovery_ack(self, timeout):
        """Wait for window closure confirmation before another transfer."""
        if not isinstance(timeout,(int,float)) or isinstance(timeout,bool) or not isfinite(timeout) or not 0 < timeout <= 60:
            raise ValueError('Délai de confirmation invalide.')
        deadline=monotonic()+timeout
        while not self._closed.is_set():
            remaining=deadline-monotonic()
            if remaining<=0:return False
            try:command=self._pending.get(timeout=min(.1,remaining))
            except Empty:continue
            if command != b'K':raise ValueError('Confirmation de fenêtre invalide.')
            return not self._closed.is_set()
        return False

    def read(self, size=1):
        if size != 1:
            raise ValueError('Taille de commande invalide.')
        while True:
            try:return self._pending.get(timeout=.1)
            except Empty:
                if self._closed.is_set():return b''
