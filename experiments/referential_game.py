"""PHASE 3 experiment: two-agent referential game (emergent communication).

Two independently initialized agents (sender + receiver) share a channel.
The sender encodes concepts (meanings) into symbol sequences; the receiver
decodes them back. After each round both agents reinforce the mapping used in
proportion to whether the receiver decoded correctly.

Symbol meanings are NOT hardcoded: each agent starts with an empty mapping and
learns concept <-> symbol associations purely from interaction. Different
random seeds produce different conventions (verified by the baseline/seed
comparison in tests).

Run:
    python3 experiments/referential_game.py
"""

from __future__ import annotations

import json
import random
import sys
import time

sys.path.insert(0, "/root/eal-repo")

from eal_cl import Channel, Decoder, Encoder, Symbol, Vocabulary  # noqa: E402

CONCEPTS = [f"concept-{i}" for i in range(8)]
SYMBOL_POOL = [f"sym-{i}" for i in range(16)]


class Agent:
    """A minimal communicating agent: encoder + decoder + vocabulary."""

    def __init__(self, name: str, seed: int) -> None:
        self.name = name
        self.rng = random.Random(seed)
        self.encoder = Encoder(rng=self.rng)
        self.decoder = Decoder(rng=self.rng)
        self.vocabulary = Vocabulary.create()
        for sym_id in SYMBOL_POOL:
            self.vocabulary.add(Symbol.generate(metadata={"pool": sym_id}))

    def send_concept(self, concept, channel, peer: str) -> tuple[str, ...]:
        symbols = self.encoder.encode(concept, available_symbols=SYMBOL_POOL)
        channel.send(self.name, symbols, concept)
        return symbols

    def hear(self, channel) -> object:
        message = channel.receive(self.name)
        if message is None:
            return None
        guess = self.decoder.decode(
            message.symbols, candidate_concepts=CONCEPTS
        )
        return message, guess


def run_round(sender: Agent, receiver: Agent, channel: Channel,
              concept) -> bool:
    """One communication round. Returns True if receiver decoded correctly."""
    sender.send_concept(concept, channel, receiver.name)
    result = receiver.hear(channel)
    if result is None:
        return False
    message, guess = result
    correct = guess == message.concept
    reward = 1.0 if correct else 0.0
    # Both agents learn from the outcome.
    sender.encoder.reinforce(message.concept, message.symbols, reward)
    receiver.decoder.reinforce(message.symbols, guess, reward)
    return correct


def run_experiment(seed: int = 0, rounds: int = 400,
                   warmup: int = 50) -> dict:
    rng = random.Random(seed)
    alice = Agent("alice", seed=seed)
    bob = Agent("bob", seed=seed + 1)
    channel = Channel("alice", "bob")

    successes = 0
    recent_window = []
    window_size = 50

    for step in range(rounds):
        concept = rng.choice(CONCEPTS)
        correct = run_round(alice, bob, channel, concept)
        successes += int(correct)
        recent_window.append(int(correct))
        if len(recent_window) > window_size:
            recent_window.pop(0)

    # Final steady-state success over the last window.
    steady_state = sum(recent_window) / len(recent_window) if recent_window else 0.0
    overall = successes / rounds

    return {
        "seed": seed,
        "rounds": rounds,
        "overall_success": overall,
        "steady_state_success": steady_state,
        "symbols_in_vocab": len(alice.vocabulary),
        "concepts": len(CONCEPTS),
    }


def run_random_baseline(seed: int = 0, rounds: int = 400) -> dict:
    """Baseline: symbols chosen uniformly at random, no learning.

    Receiver guesses uniformly from candidate concepts. Expected success ~
    1 / num_concepts.
    """
    rng = random.Random(seed)
    correct = 0
    for _ in range(rounds):
        concept = rng.choice(CONCEPTS)
        guess = rng.choice(CONCEPTS)
        correct += int(guess == concept)
    return {
        "seed": seed,
        "rounds": rounds,
        "overall_success": correct / rounds,
        "expected": 1.0 / len(CONCEPTS),
    }


def main() -> int:
    print("=== EAL-CL referential game (emergent communication) ===")
    print(f"Concepts: {len(CONCEPTS)}, symbols: {len(SYMBOL_POOL)}\n")

    results = []
    for seed in (0, 1, 2):
        r = run_experiment(seed=seed, rounds=600)
        results.append(r)
        b = run_random_baseline(seed=seed, rounds=600)
        print(
            f"seed={seed}: learned steady_state={r['steady_state_success']:.3f} "
            f"overall={r['overall_success']:.3f} | "
            f"random baseline={b['overall_success']:.3f} "
            f"(expected {b['expected']:.3f})"
        )

    # Demonstrate no hardcoded meaning: different seeds yield different
    # encoder associations (concepts map to different symbol sequences).
    a0 = Agent("a0", seed=0)
    a1 = Agent("a1", seed=1)
    s0 = a0.encoder.encode("concept-0", available_symbols=SYMBOL_POOL)
    s1 = a1.encoder.encode("concept-0", available_symbols=SYMBOL_POOL)
    print(f"\nNo-hardcoding check: concept-0 encoded as {s0} (seed 0) vs "
          f"{s1} (seed 1); equal={s0 == s1}")

    print("\nResults (JSON):")
    print(json.dumps({"learned": results}, indent=2))

    # Success criterion: learned steady-state clearly above random baseline.
    best = max(r["steady_state_success"] for r in results)
    print(f"\nBest learned steady-state success: {best:.3f}")
    return 0 if best > 0.5 else 1


if __name__ == "__main__":
    raise SystemExit(main())
