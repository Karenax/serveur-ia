"""Compatibility import; implementation belongs to kiara_shared.history_store."""
import sys
from kiara_shared import history_store as _implementation
sys.modules[__name__] = _implementation
