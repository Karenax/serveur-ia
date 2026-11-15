"""Runtime configuration and stable rendering profile for document OCR."""
import sys
from pathlib import Path

PDF_RENDER_PROFILE = {'renderer': 'pypdfium2', 'version': '5.14.0', 'pillow': '13.0.0',
                      'long_edge_pixels': 2048, 'colorspace': 'RGB', 'contract': 1}


def runtime_python():
    return Path(sys.executable)
