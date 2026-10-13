"""Expose the shared desktop/server HTTP boundary from the source checkout."""
from pathlib import Path
import sys

_client = str(Path(__file__).resolve().parents[1] / 'client-qwen')
if _client not in sys.path: sys.path.insert(0, _client)
from fred_http import BoundedHTTPServer as BoundedHTTPServer, json_body as json_body
