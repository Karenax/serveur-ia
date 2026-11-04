"""Run existing integration suites against the staged bridge before publication."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
import wireguard_access
import wg_bridge

bridge=ROOT/'toolchain/releases-staging/eg2-queue/wireguard-bridge.exe'
assert bridge.is_file()
suite=unittest.TestSuite()
for pattern in ('test_embedding_queue.py','test_eg2_api.py','test_knowledge_transport.py'):
    suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'lanceur'),pattern=pattern))
with patch.object(wireguard_access,'ENGINE',bridge), \
        patch.object(wireguard_access.Engine.__init__,'__defaults__',(bridge,)), \
        patch.object(wg_bridge,'bridge_executable',return_value=bridge):
    result=unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():raise SystemExit(1)
