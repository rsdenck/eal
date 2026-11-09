# Risks and Unresolved Research Questions

## Execution risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| No `pip` / uncertain network | Cannot install third-party Python packages | Stdlib-only initial implementation; optional packages added only when available |
| No NVIDIA GPU present | GPU-accelerated training/inference cannot run locally | CPU-first architecture; NVIDIA backend optional behind interface |
| Empty upstream repo | No existing code to preserve; greenfield only | Treat all code as new; document every decision |
| Research claims without evidence | Violates spec §6 / Definition of Done | Separate confirmed capabilities from hypotheses; require experiment results |

## Research risks (unresolved questions)

1. **Can autonomous agents develop an effective, learnable communication convention from scratch?** Not yet demonstrated. PHASE 3 will test with two agents and measurable success.
2. **Can independently trained agents achieve interoperability?** A known hard problem in emergent communication; EAL-CL includes interoperability as a requirement but success is a hypothesis, not a guarantee.
3. **Can an original programming language emerge and self-host?** Self-hosting is explicitly a long-term objective, not an initial assumption (spec §3 EAL-PL).
4. **Can language evolution preserve interoperability across versions?** Versioning and rollback mechanisms address this, but backward compatibility "where possible" means some breaking changes may be unavoidable.
5. **Which RL algorithm (GRPO, PPO, contrastive, etc.) suits emergent communication best?** To be determined empirically in PHASE 7.
6. **Can measurable improvements over conventional baselines be demonstrated?** PHASE 8 establishes baselines; negative or null results are valid scientific outcomes and must be reported honestly.

## Safety boundaries

- Humans define research objectives, constraints, evaluation criteria and safety boundaries.
- Secure execution and communication: sandboxing, resource limits, established cryptography only.
- No custom cryptography as a replacement for authenticated encryption.
- All telemetry real; no synthetic data presented as experimental results.
