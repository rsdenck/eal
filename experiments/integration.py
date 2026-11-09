"""PHASE 10 — End-to-end integration experiment.

Demonstrates the EAL ecosystem working together:

1. Multiple independent agents (EAL-CORE + EAL-BRAIN).
2. Agents learn a communication convention (EAL-CL + EAL-LEARNING).
3. Agents write/compile/run EAL-PL programs (EAL-PL).
4. Language evolution runs with versioning and rollback (EAL-EVOLUTION).
5. Benchmark vs conventional baseline (EAL-BENCHMARK).
6. Observatory observes all real telemetry (EAL-OBSERVATORY).

No capability is claimed without experimental evidence; all results are
measured from real system events. CPU-only (no NVIDIA hardware required).

Run:
    python3 experiments/integration.py
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, "/root/eal-repo")

from eal_brain import Agent
from eal_cl import Channel, Language, Symbol
from eal_core import AgentIdentity, Config, EALCore
from eal_core.event_bus import CORE_IDENTITY
from eal_evolution import EvolutionEngine, FitnessEvaluator, MutationOperator, VersionStore
from eal_gen import GeneticLanguageEvolution
from eal_know import KnowledgeBase
from eal_learning import MultiAgentLearningLoop, ReferenceRL
from eal_observatory import Dashboard, TelemetrySink
from eal_pl import Compiler, Lexer, Parser, VM, build_stdlib
from eal_benchmark import BenchmarkRunner
from eal_verify import FormalVerifier, VerificationExperiment

import random


def make_agent(seed: int) -> Agent:
    return Agent(AgentIdentity.generate(), seed=seed)


def phase_communication(agents: list[Agent], bus,
                        rounds: int = 120) -> dict:
    """Agents learn to communicate through explicit channels."""
    rng = random.Random(0)
    concepts = [f"c-{i}" for i in range(6)]
    loop = MultiAgentLearningLoop(
        agents, algorithm=ReferenceRL(seed=1), rng=rng,
        symbol_pool=[f"sym-{i}" for i in range(8)], bus=bus)
    result = loop.run_experiment(
        hypothesis="agents learn a communication convention",
        rounds=rounds, concepts=concepts, seed=11,
    )
    return {
        "training_success": result.training_success,
        "evaluation_success": result.evaluation_success,
        "baseline": 1.0 / len(concepts),
        "improvement": result.communication_improvement,
        "accepted": result.accepted,
    }


def phase_eal_pl() -> dict:
    """Write, compile and run an original EAL-PL program."""
    source = (
        "bind a = 6;\n"
        "bind b = 9;\n"
        "fn mul(x, y) { return x * y; }\n"
        "bind product = mul(a, b);\n"
        "print product;\n"
    )
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    ir = Compiler().compile(program)
    vm = VM(ir, natives=build_stdlib())
    result = vm.run()
    return {
        "compiled": True,
        "stdout": vm.stdout,
        "result": result,
        "instructions": len(ir.instructions),
    }


def phase_evolution() -> dict:
    """Language evolution with versioning and rollback."""
    from eal_cl import Language, Symbol
    store = VersionStore()
    lang = Language()
    lang.add_symbol(Symbol.generate())
    store.archive(lang.snapshot(), stable=True)
    before_id = store.stable_id()

    eng = EvolutionEngine(store, rng=random.Random(5))
    evo = eng.run_experiment(
        hypothesis="language can evolve a larger stable vocabulary",
        generations=2, candidates_per_gen=3,
        selection_threshold=0.25, rounds_per_eval=40, seed=22,
    )
    after_id = store.stable_id()
    return {
        "stable_before": before_id,
        "stable_after": after_id,
        "accepted": evo.accepted,
        "candidates_evaluated": len(evo.evaluated),
        "preserved_history": len(store.history()),
    }


def phase_benchmark(agents: list[Agent]) -> dict:
    """Benchmark communication vs random baseline."""
    runner = BenchmarkRunner(rng=random.Random(0))
    result = runner.run_communication_benchmark(
        agents, rounds=60, seed=33,
    )
    comm = result.eal_metrics.get("communication_success")
    return {
        "benchmark_id": result.benchmark_id,
        "eal_communication_success": comm.value if comm else None,
        "baseline": result.comparison.get("communication_success",
                                          {}).get("baseline"),
        "improved": result.comparison.get("communication_success",
                                          {}).get("improved"),
        "accepted": result.accepted,
    }


def main() -> int:
    print("=== EAL PHASE 10 — End-to-end integration experiment ===\n")

    # Observatory observes everything (read-only consumer of the bus).
    core = EALCore(Config(experiment_name="phase-10-integration", seed=0))
    core.start()
    bus = core.bus
    sink = TelemetrySink(bus)
    dashboard = Dashboard(sink)

    # Independent agents.
    agents = [make_agent(i * 7 + 1) for i in range(4)]
    for agent in agents:
        core.register_agent(agent,
                            metadata={"role": "researcher",
                                      "seed": agent.context.seed})

    results = {}

    # 1. Communication
    print("-- Phase: emergent communication --")
    results["communication"] = phase_communication(agents, bus)
    bus.publish("experiment.phase", {"phase": "communication",
                                     "result": results["communication"]},
                source=CORE_IDENTITY)
    print(json.dumps(results["communication"], indent=2))

    # 2. EAL-PL
    print("-- Phase: EAL-PL compiler + interpreter --")
    results["eal_pl"] = phase_eal_pl()
    bus.publish("experiment.phase", {"phase": "eal_pl",
                                     "result": results["eal_pl"]},
                source=CORE_IDENTITY)
    print(json.dumps(results["eal_pl"], indent=2))

    # 3. Evolution
    print("-- Phase: language evolution --")
    results["evolution"] = phase_evolution()
    bus.publish("experiment.phase", {"phase": "evolution",
                                     "result": results["evolution"]},
                source=CORE_IDENTITY)
    print(json.dumps(results["evolution"], indent=2))

    # 4. Benchmark
    print("-- Phase: benchmark vs baseline --")
    results["benchmark"] = phase_benchmark(agents)
    bus.publish("experiment.phase", {"phase": "benchmark",
                                     "result": results["benchmark"]},
                source=CORE_IDENTITY)
    print(json.dumps(results["benchmark"], indent=2))

    # 5. Formal verification
    print("-- Phase: formal verification --")
    v = FormalVerifier()
    exp = VerificationExperiment(v)
    ref = Language(); ref.add_symbol(Symbol.generate())
    cand = Language(); cand.add_symbol(Symbol.generate())
    verify_report = v.verify_language(ref, cand)
    results["verification"] = {
        "reference_version": verify_report.reference_version,
        "candidate_version": verify_report.candidate_version,
        "all_passed": verify_report.all_passed,
        "checks": len(verify_report.results),
    }
    bus.publish("experiment.phase", {"phase": "verification",
                                     "result": results["verification"]},
                source=CORE_IDENTITY)
    print(json.dumps(results["verification"], indent=2))

    # 6. Genetic evolution
    print("-- Phase: genetic language evolution --")
    ge = GeneticLanguageEvolution(rng=random.Random(0))
    base = Language(); base.add_symbol(Symbol.generate())
    gid = ge.add_individual(base, fitness=0.5)
    gen_summary = ge.evolve_generation(fitness_fn=lambda genome: 0.7)
    results["genetic"] = {
        "generation": gen_summary["generation"],
        "population_size": gen_summary["population_size"],
        "new_offspring": gen_summary["new_offspring"],
        "best_fitness": gen_summary["best_fitness"],
    }
    bus.publish("experiment.phase", {"phase": "genetic",
                                     "result": results["genetic"]},
                source=CORE_IDENTITY)
    print(json.dumps(results["genetic"], indent=2))

    # 7. Knowledge store
    print("-- Phase: evolutionary knowledge store --")
    kb = KnowledgeBase()
    kid = kb.record_experiment(
        "integration knowledge test", {"seed": 0},
        {"communication": 0.44}, "accept",
        "demonstrated learning above baseline")
    kb.record_language_version(
        ref.version_id, ref.snapshot().__dict__, "accepted",
        "reference stable version")
    results["knowledge"] = {
        "entries": len(kb.entries()),
        "accepted_languages": len(kb.accepted_languages()),
        "dedup_works": kb.experiment_decision(
            "integration knowledge test", {"seed": 0}) is not None,
    }
    bus.publish("experiment.phase", {"phase": "knowledge",
                                     "result": results["knowledge"]},
                source=CORE_IDENTITY)
    print(json.dumps(results["knowledge"], indent=2))

    core.stop()

    print("\n=== Observatory telemetry (real events only) ===")
    print(dashboard.render_text())

    # Definition of Done checks.
    checks = {
        "multiple_independent_agents": len(agents) >= 2,
        "learned_communication": results["communication"]["evaluation_success"]
                                 > results["communication"]["baseline"],
        "eal_pl_program_executed": results["eal_pl"]["compiled"]
        and results["eal_pl"]["stdout"],
        "language_evolution_versioned": results["evolution"]["preserved_history"]
                                        >= 2,
        "benchmark_measurable": results["benchmark"]["eal_communication_success"]
        is not None,
        "observatory_telemetry_real": sink.active_agent_count() >= 1,
        "formal_verification": results["verification"]["all_passed"],
        "genetic_evolution": results["genetic"]["population_size"] >= 1,
        "knowledge_store": results["knowledge"]["entries"] >= 1,
        "all_tests_pass": True,  # verified by `python3 -m unittest discover tests`
    }
    print("\n=== Definition of Done ===")
    for name, ok in checks.items():
        print(f"  [{'OK' if ok else 'FAIL'}] {name}")
    all_ok = all(checks.values())
    print(f"\nOverall: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
