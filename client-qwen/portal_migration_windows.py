"""Experimental private-pipe adapter for isolated recovery windows.

The caller owns the desktop profile lock, all origin ports and the control
stream. No token or data value is logged.
"""
from contextlib import contextmanager
from pathlib import Path

from portal_migration_job import MigrationJobError
from portal_origin_session import transfer_offer


class RecoveryWindows:
    def __init__(self, identity, output, control, qt_storage, initialization_script,
                 *, helper=None, environment=None, startup_timeout=45):
        self.identity=identity;self.output=output;self.control=control
        self.storage=None if qt_storage is None else Path(qt_storage)
        self.script=Path(initialization_script)
        if (not hasattr(output,'write') or not hasattr(output,'flush') or not hasattr(control,'wait_recovery_ack')
                or not self.script.is_absolute()
                or type(startup_timeout) not in (int,float) or not 0 < startup_timeout <= 60):
            raise ValueError('Contrôle de fenêtres invalide.')
        self.startup_timeout=startup_timeout

    @contextmanager
    def open(self, broker, job, destination, cancelled):
        """Announce only validated instructions and wait for closure on exit."""
        announced=False
        class Windows:
            shown=False
            startup_timeout=self.startup_timeout
            def is_running(inner):
                return not cancelled()
            def show_review(inner):
                if inner.shown:return inner.is_running()
                if not announced or not inner.is_running():return False
                self.output.write('KIARA_RELAY_ORIGIN_REVIEW\n');self.output.flush()
                if not self.control.wait_recovery_ack(15) or not inner.is_running():return False
                inner.shown=True
                return True
        try:
            if job['engine']!='tauri':
                raise MigrationJobError('Cette ancienne origine ne peut pas être migrée automatiquement ; ses données sont conservées.')
            if cancelled():raise MigrationJobError('Migration interrompue ; les sources sont conservées.')
            self.output.write(transfer_offer(self.identity,broker.token,job['port'],destination,job['engine'],broker.result_mode)+'\n')
            self.output.flush();announced=True
            yield Windows()
        finally:
            if announced and not cancelled():
                self.output.write('KIARA_RELAY_ORIGIN_TRANSFER_DONE\n');self.output.flush()
                if not self.control.wait_recovery_ack(15):
                    raise MigrationJobError('Fermeture des fenêtres non confirmée ; les sources sont conservées.')
