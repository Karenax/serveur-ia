"""Compatibility import; implementation belongs to kiara_shared.voice_runtime."""
import sys
from kiara_shared import voice_runtime as _implementation
sys.modules[__name__] = _implementation
