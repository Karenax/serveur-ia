"""Compatibility import; implementation belongs to kiara_shared.attachments."""
import sys
from kiara_shared import attachments as _implementation
sys.modules[__name__] = _implementation
