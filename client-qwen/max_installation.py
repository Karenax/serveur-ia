"""Compatibility import; implementation belongs to kiara_shared.voice_packs."""
import sys
from kiara_shared import voice_packs as _implementation
sys.modules[__name__] = _implementation
