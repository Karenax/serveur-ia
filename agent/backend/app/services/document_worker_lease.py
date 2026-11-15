"""Held OS file lock, tied to one SQLite queue. Metadata is never authority."""
import os
from pathlib import Path
import stat


class WorkerLease:
    def __init__(self, database, *, namespace='worker'):
        if namespace not in {'worker', 'publication'}:
            raise ValueError('Espace de verrou documentaire invalide')
        database=Path(database).absolute()
        for part in (database,*database.parents):
            if part.is_symlink() or part.is_junction():
                raise ValueError('Base documentaire liée : verrou de worker refusé')
        if not database.is_file() or database.stat().st_nlink!=1:
            raise ValueError('Base documentaire régulière et sans alias requise')
        database=database.resolve(strict=True)
        self.path=database.with_name(database.name+f'.document-{namespace}.lock')
        self.stream=None

    def acquire(self):
        if self.stream is not None:
            return True
        for part in (self.path,*self.path.parents):
            if part.is_symlink() or part.is_junction():
                raise ValueError('Verrou de worker hors du stockage Agent')
        if not self.path.parent.is_dir():
            raise ValueError('Dossier de base documentaire absent')
        stream=self.path.open('a+b')
        try:
            info=os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1:
                raise ValueError('Fichier de verrou régulier et exclusif requis')
            if info.st_size==0:
                stream.write(b'\0')
                stream.flush()
            stream.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            stream.close()
            return False
        except Exception:
            stream.close()
            raise
        self.stream=stream
        return True

    def close(self):
        if self.stream is None:
            return
        stream,self.stream=self.stream,None
        try:
            stream.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
        finally:
            stream.close()
