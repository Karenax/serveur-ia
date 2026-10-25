"""Use the same optional runtime controller as the Windows client."""
import importlib.util
from pathlib import Path

_source = Path(__file__).resolve().parents[1]/'client-qwen/advanced_voice.py'
_spec = importlib.util.spec_from_file_location('kiara_advanced_voice', _source)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
AdvancedVoice = _module.AdvancedVoice
