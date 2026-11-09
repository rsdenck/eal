# Technology Decisions

## Implementation language: Python 3.11 (standard library only)

**Rationale:**
- The local environment has Python 3.11 but no `pip`, no guaranteed network to PyPI, and no pre-installed ML packages (only `numpy` in system dist-packages).
- Using the standard library only guarantees that EAL-CORE through EAL-CL can be developed, tested, and reproduced on CPU without any external dependency or GPU.
- NVIDIA technologies (NeMo, PyTorch, TensorRT-LLM, Dynamo, CUDA, NCCL) are treated as an **optional acceleration layer**, introduced behind strict interfaces only when hardware and licensing are verified (spec §4). Absent hardware/libraries → graceful CPU fallback, never a hard failure.

## NVIDIA stack (future, optional)

Per spec §4, prioritize NVIDIA technologies but do not assume open-source availability and verify licensing/hardware compatibility before implementation:
- NVIDIA Nemotron, NeMo Framework, NeMo RL, NeMo Fabric, NeMo Helix, NIM, TensorRT-LLM, Dynamo, CUDA, NCCL.

Integration approach: abstract `ModelInference`, `Trainer`, and `Accelerator` interfaces in `eal_learning` and `eal_brain`. Concrete NVIDIA backends implement these interfaces; a CPU reference backend is always present. No code path requires NVIDIA hardware.

## Serialization and reproducibility

- Experiment artifacts and language versions are serialized to deterministic JSON (no `pickle`, no timestamps embedded in content-addressed identifiers).
- Each experiment record pins: code version (git SHA), config, random seed, library/environment snapshot where available.
- Stable language versions are archived under `experiments/` before any mutation; rollback restores the archived version byte-for-byte.

## Testing

- Python `unittest` (stdlib) for unit and integration tests.
- No external test runner assumed; tests run with `python -m unittest discover`.

## Version control

- Single branch `main`; commits are logically separated units (docs, core, CL, SC, PL, etc.).
- No force push to stable branches; history preserved for reproducibility.

## Decisions deferred

- GUI/observatory backend (web vs. terminal) — decided in PHASE 9.
- Specific RL algorithm (GRPO vs. PPO vs. custom) — decided in PHASE 7 after baseline experiments.
- Specific cryptographic library for EAL-SC — decided in PHASE 4 (must be an established library; never custom crypto as replacement for authenticated encryption).
