"""EAL-CORE configuration.

Configuration is a dataclass-based, validated, JSON-serializable object.
Every experiment pins its configuration so runs are reproducible: identical
config + identical code version + identical seed => identical behavior
(modulo explicitly stochastic components that record their own seed).

No third-party packages are required: only the Python standard library.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields, asdict
from typing import Any


@dataclass
class Config:
    """Top-level EAL configuration.

    Attributes:
        experiment_name: Human-readable experiment identifier.
        seed: Master random seed for reproducibility.
        log_level: One of DEBUG, INFO, WARNING, ERROR.
        max_agents: Upper bound on concurrently registered agents.
        enable_telemetry: Whether the observatory/telemetry sink is active.
        nvidia_acceleration: Request NVIDIA-accelerated backends where
            available. Absent hardware/libraries degrades gracefully to CPU;
            this flag never forces a hard failure.
        modules: Set of module names enabled for this run.
    """

    experiment_name: str = "default"
    seed: int = 0
    log_level: str = "INFO"
    max_agents: int = 1024
    enable_telemetry: bool = True
    nvidia_acceleration: bool = False
    modules: set[str] = field(default_factory=lambda: {
        "eal_core",
        "eal_brain",
        "eal_cl",
    })

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate configuration invariants; raise ValueError on failure."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR"}
        if self.log_level not in valid_levels:
            raise ValueError(
                f"config.log_level must be one of {sorted(valid_levels)}, "
                f"got {self.log_level!r}"
            )
        if not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError(f"config.seed must be a non-negative int, got {self.seed!r}")
        if not isinstance(self.max_agents, int) or self.max_agents < 1:
            raise ValueError(f"config.max_agents must be a positive int, got {self.max_agents!r}")
        if not isinstance(self.modules, set) or not self.modules:
            raise ValueError("config.modules must be a non-empty set")
        if "eal_core" not in self.modules:
            raise ValueError("config.modules must include 'eal_core'")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict (sets become sorted lists)."""
        data = asdict(self)
        data["modules"] = sorted(data["modules"])
        return data

    def to_json(self, indent: int = 2) -> str:
        """Serialize to a deterministic JSON string."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Deserialize from a dict produced by :meth:`to_dict`."""
        if "modules" in data and isinstance(data["modules"], list):
            data = dict(data)
            data["modules"] = set(data["modules"])
        return cls(**data)

    @classmethod
    def from_json(cls, text: str) -> "Config":
        """Deserialize from JSON text."""
        return cls.from_dict(json.loads(text))

    def with_seed(self, seed: int) -> "Config":
        """Return a copy with a different seed (for experiment sweeps)."""
        cfg = Config.from_dict(self.to_dict())
        cfg.seed = seed
        cfg.validate()
        return cfg

    def with_module(self, name: str) -> "Config":
        """Return a copy with an additional module enabled."""
        cfg = Config.from_dict(self.to_dict())
        cfg.modules.add(name)
        cfg.validate()
        return cfg
