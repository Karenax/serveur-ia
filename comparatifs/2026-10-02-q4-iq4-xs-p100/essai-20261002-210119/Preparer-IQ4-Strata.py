"""Use the existing packer, retaining the IQ4_XS PLE key supported by the engine."""
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root / 'Strata-src' / 'tools'))
import iq_pack

# NativeDense and the PLE kernel already support GGML type 23. The generic packer's
# whitelist only contains Q2_0/Q8_0, so otherwise it would expand this key to BF16.
# All other compatibility conversions use the exact same tool as the Q4 baseline.
iq_pack.NATIVE_PLE_KEY.add('IQ4_XS')
raise SystemExit(iq_pack.main())
