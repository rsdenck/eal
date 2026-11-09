# PHASE 1 — Architecture Specification

**Date:** 2026-11-09  
**Status:** Proposed (pending PHASE 0 acceptance)

## 1. Design goals

- Modular core with strict interfaces; distributed services added only where technically justified (spec §7).
- CPU-based testing works without GPU or third-party packages (stdlib-only initial implementation).
- NVIDIA/ML stack is an optional, abstracted layer behind the same interfaces.
- Event-driven agent communication; deterministic functional transformations where appropriate.
- Reproducible experiments: every experiment is versioned, configured, and its inputs preserved; stable language versions are never overwritten without preserving prior state.

## 2. Module boundaries and responsibilities

| Module | Spec ref | Responsibilities | Public interface (summary) |
|--------|----------|------------------|----------------------------|
| `eal_core` | EAL-CORE | Configuration, lifecycle, subsystem coordination, event bus, agent registry | `EALCore`, `AgentRegistry`, `EventBus`, `Config` |
| `eal_brain` | EAL-BRAIN | Agent state, memory interfaces, model inference, learning interfaces, identity, independent execution contexts | `Agent`, `AgentIdentity`, `AgentState`, `Memory`, `ExecutionContext` |
| `eal_cl` | EAL-CL | Emergent communication language: discrete symbols, dynamic vocabulary, emergent grammar, semantic composition, contextual representations, encode/decode, bidirectional communication, interoperability, versioning | `Symbol`, `Vocabulary`, `Grammar`, `Language`, `Encoder`, `Decoder`, `Channel` |
| `eal_sc` | EAL-SC | Private communication: agent identities, private protocol conventions, binary/symbolic representations, message authentication, key management, secure transport, replay protection, versioning, integrity | `PeerIdentity`, `SessionKey`, `AuthenticatedChannel`, `KeyManager` |
| `eal_pl` | EAL-PL | Original programming language: grammar, lexer, parser, AST, semantic analysis, type system, IR, standard library, error handling, debugging, tests, docs, package system | `GrammarSpec`, `Lexer`, `Parser`, `AST`, `SemanticAnalyzer`, `TypeChecker`, `Program` |
| `eal_compiler` | EAL-COMPILER | Compilation toolchain: reproducible compilation, IR, diagnostics, validation | `Compiler`, `IR`, `Diagnostic`, `Validator` |
| `eal_runtime` | EAL-RUNTIME | Execution environment: memory management, process isolation, execution control, resource limits, sandboxing, diagnostics, standard execution interfaces | `VM`, `Runtime`, `Sandbox`, `ResourceLimits` |
| `eal_evolution` | EAL-EVOLUTION | Language evolution: detect limitations, propose structures, generate mutations, test symbols/operators, experiment with semantics, evaluate performance, compare candidates, select, preserve history, revert | `EvolutionEngine`, `Candidate`, `FitnessEvaluator`, `VersionStore`, `MutationOperator` |
| `eal_learning` | EAL-LEARNING | Learning mechanisms: multi-agent RL, emergent communication, discrete/continuous representations, contrastive learning, GRPO; separate train/eval/infer | `Learner`, `Trainer`, `Evaluator`, `InferenceEngine` |
| `eal_benchmark` | EAL-BENCHMARK | Measurement: communication success, semantic preservation, bits/message, message length, latency, cost, generalization, vocabulary stability, compositionality, learning speed, interoperability, expressiveness, compiler correctness | `Benchmark`, `Metric`, `Baseline`, `Result` |
| `eal_observatory` | EAL-OBSERVATORY | Real-time visualization & telemetry from real system events only | `Observatory`, `TelemetrySink`, `EventRecorder` |

## 3. Dependency graph (logical, acyclic)

```
eal_core  ◄── (imported by) ── all other modules
eal_brain ◄── eal_cl, eal_sc, eal_learning
eal_cl    ◄── eal_sc, eal_evolution, eal_learning, eal_benchmark
eal_sc    ◄── eal_evolution, eal_benchmark
eal_pl    ◄── eal_compiler, eal_runtime
eal_compiler ◄── eal_pl
eal_runtime ◄── eal_pl, eal_sc
eal_evolution ◄── eal_cl, eal_pl, eal_brain
eal_learning ◄── eal_cl, eal_pl, eal_brain, eal_evolution
eal_benchmark ◄── eal_cl, eal_pl, eal_runtime, eal_sc
eal_observatory ◄── all (read-only telemetry consumer)
```

- `eal_core` is the only module imported by every other module; it imports nothing from the feature modules (keeps the core minimal and testable).
- `eal_observatory` is a pure consumer (read-only) of telemetry events; it does not influence execution.

## 4. Core architecture concepts

### 4.1 Agent
An agent is an independent identity with its own state, brain, and execution context. Agents communicate only through explicit channels (`eal_cl.Channel` / `eal_sc.AuthenticatedChannel`). Assigning different names to identical prompts does **not** create independent cognitive systems; each agent instance maintains independent state.

### 4.2 Language / Grammar
A language is a versioned object `(grammar, vocabulary, semantics)`. Symbols have no hardcoded meaning; meaning is learned through interaction. Grammar mutations produce candidate versions; the evolution engine evaluates and selects among them.

### 4.3 Experiment
An experiment is a reproducible record: `{hypothesis, config, seed, code_version, baseline, results, limitations, decision}`. Experiments are stored under `experiments/` and never mutate a stable language version without archiving the prior state.

### 4.4 Event bus
All inter-agent and inter-module communication flows through `eal_core.EventBus`. The observatory subscribes to the bus for telemetry; telemetry originates only from real system events.

## 5. Interfaces (strict)

Python `abc.ABC` / `typing.Protocol` are used to define strict interfaces. Modules depend on interfaces, not concrete implementations, enabling CPU/GPU and mock/test swaps.

Example boundary (illustrative; implemented in PHASE 2+):

```python
class Channel(Protocol):
    def send(self, agent_id: AgentIdentity, payload: bytes) -> MessageId: ...
    def receive(self, agent_id: AgentIdentity) -> Message | None: ...
```

## 6. Technology decisions (summary)

| Decision | Rationale |
|----------|-----------|
| Language: Python 3.11, stdlib only | No pip/network guaranteed; guarantees CPU-based testing; rapid research iteration |
| NVIDIA stack | Optional abstracted layer; verified docs/licensing/hardware before use (spec §4) |
| Serialization | JSON / `pickle`-free deterministic binary for experiment artifacts (reproducibility) |
| Testing | `unittest` (stdlib); no external test framework assumed |
| VCS | Git on `main`; logically separated commits |

Full details: `docs/TECHNOLOGY_DECISIONS.md`.

## 7. Roadmap (implementation order)

PHASE 2 (EAL-CORE) → PHASE 3 (EAL-CL) → PHASE 4 (EAL-SC) → PHASE 5 (EAL-PL) → PHASE 6 (EAL-EVOLUTION) → PHASE 7 (EAL-LEARNING) → PHASE 8 (EAL-BENCHMARK) → PHASE 9 (EAL-OBSERVATORY) → PHASE 10 (Integration).

See `docs/ROADMAP.md` for per-phase tasks and acceptance criteria.

## 8. Risks and unresolved research questions

See `docs/RISKS.md`.
