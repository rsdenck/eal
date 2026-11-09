# EAL — Emergent Autonomous Language

An autonomous language research and computational ecosystem.

## Mission

Develop an ecosystem capable of creating, learning, using, evaluating and evolving its own:

1. Inter-agent communication language (EAL-CL)
2. Programming language (EAL-PL)
3. Private communication encoding system (EAL-SC)
4. Compiler and interpreter (EAL-COMPILER / EAL-RUNTIME)
5. Runtime and execution environment (EAL-RUNTIME)
6. Language evolution mechanisms (EAL-EVOLUTION)
7. Agent learning and optimization mechanisms (EAL-LEARNING)

EAL is **not** a conventional chatbot, an LLM wrapper, or merely an agent orchestration framework. It investigates whether autonomous AI agents can develop effective communication conventions and progressively construct their own computational language.

## Repository status (PHASE 0)

The upstream repository `https://github.com/rsdenck/eal.git` was empty (no commits, no files, no tags). This is a greenfield implementation. See `docs/PHASE_0_REPOSITORY_AUDIT.md` for the full audit.

## Development phases

| Phase | Focus | Status |
|-------|-------|--------|
| PHASE 0 | Repository audit | Complete |
| PHASE 1 | Architecture specification, dependency graph, roadmap | Complete |
| PHASE 2 | EAL-CORE: foundational infrastructure & agent lifecycle | Planned |
| PHASE 3 | EAL-CL: emergent communication environment | Planned |
| PHASE 4 | EAL-SC: private encoding, identity, authentication, secure transport | Planned |
| PHASE 5 | EAL-PL: language spec, parser, compiler, runtime | Planned |
| PHASE 6 | EAL-EVOLUTION: grammar evolution, versioning, rollback | Planned |
| PHASE 7 | EAL-LEARNING: NVIDIA training & RL infrastructure | Planned |
| PHASE 8 | EAL-BENCHMARK: reproducible experiments & baselines | Planned |
| PHASE 9 | EAL-OBSERVATORY: real telemetry & visualization | Planned |
| PHASE 10 | Integration: end-to-end experiment | Planned |

## Core principles

- Agent-generated language conventions; no hardcoded symbol meanings.
- Emergent communication rather than predefined vocabulary.
- Independent agent identities and states.
- Reproducible experiments; every change has hypothesis, config, baseline, results.
- Measurable language evolution; no fabricated telemetry.
- Versioned grammar and semantics; backward compatibility where possible.
- Secure execution and communication; established cryptography only (no custom crypto as replacement for authenticated encryption).
- NVIDIA-first AI infrastructure; modular so CPU-only testing works without GPU.
- Humans define objectives, constraints, evaluation criteria and safety boundaries.

## Technology decisions

- Implementation language: **Python 3.11**, standard library only for the initial core (no `pip`, no guaranteed network). This guarantees CPU-based testing works everywhere.
- NVIDIA/ML stack (PyTorch, NeMo, TensorRT-LLM, etc.) is an **optional, abstracted future layer** behind strict interfaces; absent hardware/libraries degrade gracefully to CPU.
- Version control: Git on `main`, with logically separated commits.

## Module layout

```
eal_core/        # EAL-CORE: architecture, lifecycle, config, event bus, agent registry
eal_brain/       # EAL-BRAIN: agent state, memory, identity, execution contexts
eal_cl/          # EAL-CL: emergent communication language (symbols, grammar, encode/decode)
eal_sc/          # EAL-SC: private communication (identities, auth, key management, transport)
eal_pl/          # EAL-PL: original programming language (grammar, lexer, parser, AST)
eal_compiler/    # EAL-COMPILER: compilation toolchain (IR, diagnostics, validation)
eal_runtime/     # EAL-RUNTIME: execution environment (VM, sandboxing, resource limits)
eal_evolution/   # EAL-EVOLUTION: language evolution engine (mutation, selection, rollback)
eal_learning/    # EAL-LEARNING: learning mechanisms (RL, representations)
eal_benchmark/   # EAL-BENCHMARK: measurement & baseline comparison
eal_observatory/ # EAL-OBSERVATORY: telemetry & visualization
experiments/     # reproducible experiment configs & results
docs/            # architecture, API, research records
tests/           # unit & integration tests
```

## Research methodology

Every significant change must include: research hypothesis, implementation, experiment configuration, baseline comparison, reproducible execution, evaluation results, limitations, and an accept/reject/investigate decision. Confirmed capabilities are separated from research hypotheses. No capability is claimed without experimental evidence.

## Definition of done

EAL is complete when it demonstrates: multiple independently operating agents, a learned communication convention, successful cross-agent decoding, an independently learnable language, an original programming language, a working compiler/interpreter, executable EAL-PL programs, a versioned evolution engine, reproducible experiments, secure communication, measurable improvements against baselines, and complete technical documentation.

## License

Proprietary research — verify NVIDIA technology licensing and hardware compatibility before implementation (see `docs/TECHNOLOGY_DECISIONS.md`).
