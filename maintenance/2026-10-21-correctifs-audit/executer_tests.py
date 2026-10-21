"""Run unchanged server suites with disposable databases on the private SSD.

The production root and model paths stay unchanged. Only unittest fixtures that
explicitly request a temporary directory under lanceur are redirected to SSD.
"""
import faulthandler
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
from wg_crypto import private_directory

scratch=Path(os.environ['LOCALAPPDATA'])/'Fred/validation-audit-20261021'
private_directory(scratch)
original=tempfile.TemporaryDirectory
def temporary(*args,**kwargs):
    args=list(args)
    selected=kwargs.get('dir',args[2] if len(args)>2 else None)
    if selected is not None and Path(selected).resolve()==(ROOT/'lanceur').resolve():
        if len(args)>2:args[2]=scratch
        else:kwargs['dir']=scratch
    return original(*args,**kwargs)
tempfile.TemporaryDirectory=temporary
tempfile.tempdir=str(scratch)
faulthandler.dump_traceback_later(120,repeat=True)
suite=unittest.defaultTestLoader.discover(str(ROOT/'lanceur'))
result=unittest.TextTestRunner(verbosity=2).run(suite)
faulthandler.cancel_dump_traceback_later()
sys.exit(not result.wasSuccessful())
