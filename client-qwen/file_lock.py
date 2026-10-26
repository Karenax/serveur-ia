"""Compatibility import; implementation belongs to kiara_shared.file_lock."""
import sys
from kiara_shared import file_lock as _implementation
sys.modules[__name__] = _implementation
