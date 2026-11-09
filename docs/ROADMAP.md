# Development Roadmap

## PHASE 0 — Repository audit (complete)
- [x] Inspected `https://github.com/rsdenck/eal.git` — empty (no commits, files, branches, tags)
- [x] Audited local environment (Python 3.11 stdlib, no pip, no GPU, no ML packages)
- [x] Conclusion: greenfield, CPU-first, stdlib-only initial implementation

## PHASE 1 — Architecture (complete)
- [x] Module boundaries and responsibilities
- [x] Dependency graph
- [x] Technology decisions
- [x] Roadmap, risks, initial tasks (this document)

## PHASE 2 — EAL-CORE (foundational infrastructure & agent lifecycle)
Tasks:
- [ ] `Config`: dataclass-based configuration with validation, loadable from JSON/dict
- [ ] `EventBus`: publish/subscribe, ordered delivery, subscriber identity
- [ ] `AgentRegistry`: create/register/resolve/drop agents by identity
- [ ] `EALCore`: subsystem coordinator, start/stop lifecycle, wiring
- [ ] `AgentIdentity`: immutable, unforgeable agent identifier
- [ ] Unit tests: config validation, event bus publish/subscribe, registry CRUD
- [ ] Experiment record skeleton: hypothesis/config/seed/results/decision

Acceptance criteria:
- Two agents can be registered and addressed by identity
- Events published on the bus reach subscribers
- Configuration loads and validates deterministically

## PHASE 3 — EAL-CL (emergent communication)
Tasks:
- [ ] `Symbol`: discrete learnable symbol (opaque id + optional bit pattern)
- [ ] `Vocabulary`: dynamic symbol set, add/remove, versioned
- [ ] `Grammar`: symbol-composition rules, versioned, no hardcoded semantics
- [ ] `Language`: (grammar, vocabulary) pair with version id
- [ ] `Encoder`/`Decoder`: message ↔ symbol sequence, learnable mapping
- [ ] `Channel`: bidirectional message transport between two agents
- [ ] Two-agent communication experiment: sender encodes, receiver decodes, measure success
- [ ] Baseline: random-symbol communication vs. learned convention

Acceptance criteria:
- A learned communication convention exists between two independently initialized agents
- Receiver successfully decodes a message sent by the sender
- Symbol meanings are not hardcoded (demonstrated by re-running with different seeds → different conventions)
- Communication success measurable and compared to baseline

## PHASE 4 — EAL-SC (private communication)
Tasks:
- [ ] `PeerIdentity`: agent-specific cryptographic identity
- [ ] `SessionKey`: ephemeral key management
- [ ] `AuthenticatedChannel`: message authentication + integrity (established library; no custom crypto)
- [ ] Replay protection (nonces/sequence numbers)
- [ ] Binary and symbolic message representations
- [ ] Protocol versioning
- [ ] Secure transport abstraction

Acceptance criteria:
- Messages authenticated and integrity-verified
- Replayed messages rejected
- Distinction documented between learned private encodings and cryptographic security

## PHASE 5 — EAL-PL (programming language)
Tasks:
- [ ] Formally documented language specification (`docs/eal_pl_spec.md`)
- [ ] Original grammar (not a rename of Python/Rust/Go)
- [ ] Lexer, Parser, AST
- [ ] Semantic analysis, type system
- [ ] Intermediate representation
- [ ] Compiler + interpreter/VM
- [ ] Standard library, error handling, debugging support
- [ ] Automated tests, documentation, package system

Acceptance criteria:
- Executable programs written in EAL-PL run on the interpreter/VM
- Original grammar documented

## PHASE 6 — EAL-EVOLUTION (language evolution engine)
Tasks:
- [ ] Detect limitations in existing language versions
- [ ] Propose new structures; generate grammar mutations
- [ ] Test new symbols/operators; experiment with semantic changes
- [ ] Evaluate communication performance & PL capabilities; compare candidates
- [ ] Select successful candidates; preserve historical versions
- [ ] Revert unsuccessful experiments
- [ ] Mutation, crossover, selection, fitness evaluation

Acceptance criteria:
- Versioned language evolution with rollback
- No stable version overwritten without preserving prior state
- Reproducible evolution experiments

## PHASE 7 — EAL-LEARNING (NVIDIA training & RL)
Tasks:
- [ ] Multi-agent reinforcement learning integration
- [ ] Emergent communication learning objectives
- [ ] Discrete and continuous latent representation learning
- [ ] Contrastive learning
- [ ] GRPO / appropriate RL algorithms
- [ ] Separate training, evaluation, inference

Acceptance criteria:
- CPU reference backend works without NVIDIA hardware
- NVIDIA backend swappable behind interface

## PHASE 8 — EAL-BENCHMARK (measurement & baselines)
Tasks:
- [ ] Metrics: communication success, semantic preservation, bits/message, message length, latency, cost, generalization, vocabulary stability, compositionality, learning speed, interoperability, PL expressiveness, compiler correctness
- [ ] Conventional communication baselines
- [ ] Reproducible experiment execution

Acceptance criteria:
- Measurable improvements (or documented lack thereof) against baselines
- No fabricated telemetry

## PHASE 9 — EAL-OBSERVATORY (telemetry & visualization)
Tasks:
- [ ] Real-time telemetry from real system events only
- [ ] Visualization: active agents, exchanges, emerging symbols, vocabulary/grammar changes, versions, learning progress, evolution experiments, compilation, runtime metrics, GPU utilization, benchmark results

Acceptance criteria:
- All telemetry originates from real system events; no synthetic data presented as results

## PHASE 10 — Integration
- [ ] End-to-end experiment: agents learn communication, write/compile/run EAL-PL programs, evolve language, benchmark results observed
