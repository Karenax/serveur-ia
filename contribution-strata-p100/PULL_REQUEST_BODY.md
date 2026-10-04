The resident expert mode currently rejects layer splits, and GP100 cannot use the BF16 cuBLAS prompt product.
This opt-in experiment shares a strictly pinned RAM complement across fixed GPU caches, permits CPU computation
of cache misses, and converts BF16 prompt operands to FP16 on sm_60 with FP32 accumulation.

On a Windows Threadripper PRO 3955WX / 128 GiB DDR4-3200 / two PCIe 3.0 x16 P100 16 GiB workstation,
paired UD-Q4_K_XL short prompts improved from 8.72/10.95 to 28.70/35.16 decode tok/s when the CPU computed
all RAM misses. Four miss-share settings used one binary, fixed caches, fifteen workers plus the host,
the same Q2 MTP draft and the same two 256-token requests, twice each. These are preliminary measurements
on one workstation; no wider performance or quality guarantee is claimed.

The contribution includes:

- Strict residency validation and fixed-cache requirements behind `STRATA_P100_RAM_SPLIT=1`; a separate
  `STRATA_P100_HYBRID=1` opt-in for CPU misses, and refusal of unintended CPU fallback in GPU-only mode.
- Windows locked PLE RAM and sequential native-projection loading with per-layer byte checks.
- A 64-blob experimental staging reserve; ordinary runs retain sixteen blobs.
- The GP100 prompt fallback, matching partial-metadata shard support, regression tests and decode expert counters.
- A portable Q8 draft adapter, exact benchmark protocol, sixteen numeric run records, restart validation,
  a reproduction harness and configuration template.

Report: `bench/results/2026-10-02-p100-resident-hybrid/README.md`.

Validation: isolated CUDA 12.4 / sm_60 build; `gguf_split_test`, `file_expert_source_test`,
`native_dense_ple_key_test` and `prefill_p100_test` all passed. Native expert parity for q4_K/q5_1,
q4_K/q8_0 and q5_K/q8_0 reported zero failures. Python syntax checks passed.
The original generic MMQ test did not pass its Q8_0 screen on sm_60; the validated path is the FP16 fallback.

Draft because the measured implementation is based on 0.1.35 (`d9ab843`) and still needs revalidation
against 0.1.36, a broader prompt corpus, long-context coverage and paired MTP-on/off tests. The published
source scopes the staging/log changes and adds regression cases after the fixed-binary measurement;
the report distinguishes these cleanups from the archived throughput results.
