"""Run isolated API fixtures on the temporary volume, preserving production I/O."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
import test_remote

suite=unittest.TestSuite()
for pattern in ('test_eg2_runtime.py','test_eg2_api.py','test_embedding_queue.py','test_knowledge_transport.py'):
    suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'lanceur'),pattern=pattern))
with tempfile.TemporaryDirectory(prefix='kiara-eg2-api-fixtures-') as folder:
    with patch.object(test_remote,'HOME',Path(folder)):
        result=unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():raise SystemExit(1)
