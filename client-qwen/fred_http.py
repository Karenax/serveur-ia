"""Compatibility import; implementation belongs to kiara_shared.http."""
import sys
from kiara_shared import http as _implementation
sys.modules[__name__] = _implementation
