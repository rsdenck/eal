"""Model inference interfaces for EAL-BRAIN.

:class:`ModelInference` is the strict interface agents use to run inference.
:class:`DeterministicInference` is a stdlib reference implementation (no NVIDIA
hardware required). Production NVIDIA backends (NeMo / TensorRT-LLM / NIM)
implement the same interface behind an optional adapter; CPU fallback is always
present so hardware absence never blocks testing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ModelInference(ABC):
    """Strict inference interface.

    Implementations must be deterministic given the same inputs and weights,
    so experiments are reproducible.
    """

    @abstractmethod
    def infer(self, input_data: Any,
              parameters: dict[str, Any] | None = None) -> Any:
        raise NotImplementedError

    @abstractmethod
    def supports_gpu(self) -> bool:
        raise NotImplementedError


class DeterministicInference(ModelInference):
    """Reference CPU inference: a fixed deterministic transformation.

    Not a real neural model; used so EAL-BRAIN is runnable without ML libraries
    or GPUs. Swap in an NVIDIA-backed implementation behind ModelInference when
    hardware is available.
    """

    def __init__(self, seed: int = 0) -> None:
        self.seed = seed

    def infer(self, input_data: Any,
              parameters: dict[str, Any] | None = None) -> Any:
        """Deterministically transform input_data into an output.

        The output is a pure function of (input_data, parameters, seed).
        """
        import hashlib
        import json

        payload = json.dumps(
            {"input": str(input_data), "parameters": parameters or {},
             "seed": self.seed},
            sort_keys=True,
        ).encode("utf-8")
        digest = hashlib.sha256(payload).digest()
        # Produce a bounded deterministic output vector.
        vector = [(b / 255.0) for b in digest[:8]]
        return {
            "output_vector": vector,
            "seed": self.seed,
            "deterministic": True,
            "backend": "stdlib-reference",
        }

    def supports_gpu(self) -> bool:
        return False


class NVIDIAInferencePlaceholder(ModelInference):
    """Documented placeholder for an NVIDIA inference backend.

    Not implemented: requires verifying NeMo / TensorRT-LLM / NIM licensing,
    supported versions and hardware compatibility (spec §4) before use.
    Instantiating raises NotImplementedError to avoid silently falling back.
    """

    def infer(self, input_data: Any,
              parameters: dict[str, Any] | None = None) -> Any:
        raise NotImplementedError(
            "NVIDIAInferencePlaceholder: no NVIDIA backend configured. "
            "Use DeterministicInference for CPU testing, or implement a "
            "ModelInference adapter for a verified NVIDIA stack."
        )

    def supports_gpu(self) -> bool:
        return True
