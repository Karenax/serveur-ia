"""Privacy and resource bounds of diagnostics; query growth of workspace reads."""
from contextlib import contextmanager
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from runtime_diagnostics import Diagnostics
from workspace import Workspace


class ObservabilityTests(unittest.TestCase):
    def test_diagnostics_exclude_exception_and_stderr_content_and_rotate(self):
        with tempfile.TemporaryDirectory() as folder:
            diagnostic=Diagnostics(folder);diagnostic.MAX_BYTES=1024
            for number in range(25):
                diagnostic.record('voice','read_frame',ValueError('SECRET prompt and token'),
                                  stderr=b'ModuleNotFoundError: SECRET filesystem path')
            for path in diagnostic.directory.iterdir():
                self.assertNotIn('SECRET',path.read_text())
                self.assertLessEqual(path.stat().st_size,1024)
            entries=diagnostic.recent()
            self.assertTrue(entries)
            self.assertEqual(entries[-1]['category'],'ModuleNotFoundError')

    def test_snapshot_select_count_does_not_grow_with_project_count(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        workspace=Workspace(temporary.name);self.addCleanup(workspace.shutdown)
        workspace.action('a',{'action':'project_create','title':'Premier'})
        original=workspace.db
        def count():
            statements=[]
            @contextmanager
            def traced(owner=None):
                with original(owner) as db:
                    db.set_trace_callback(statements.append)
                    yield db
            with patch.object(workspace,'db',traced):workspace.snapshot('a')
            return len([value for value in statements if value.lstrip().upper().startswith('SELECT')])
        initial=count()
        for number in range(12):workspace.action('a',{'action':'project_create','title':str(number)})
        self.assertEqual(count(),initial)
        metrics=workspace.metrics.snapshot()
        self.assertEqual(metrics['workspace_snapshot']['count'],2)
        self.assertIn('p95_ms',metrics['db_lock_wait'])


if __name__=='__main__':unittest.main()
