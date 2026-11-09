"""EAL-LEARNING package.

Public API:
    RLAlgorithm                      # strict RL algorithm interface
    ReferenceRL                      # stdlib reference RL (CPU, deterministic)
    MultiAgentLearningLoop           # coordinates independent agents learning
    MultiAgentLearningResult         # experiment outcome
    Experience                       # single learning experience

Training, evaluation and inference are strictly separated. A CPU reference
backend is provided; NVIDIA NeMo RL / GRPO backends implement RLAlgorithm and
ModelInference behind the same interfaces (spec §4, §7).
"""

from .multi_agent import (Experience, MultiAgentLearningLoop,
                          MultiAgentLearningResult, RLAlgorithm, ReferenceRL)

__all__ = [
    "Experience",
    "MultiAgentLearningLoop",
    "MultiAgentLearningResult",
    "RLAlgorithm",
    "ReferenceRL",
]
