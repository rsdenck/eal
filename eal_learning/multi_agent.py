"""EAL-LEARNING: learning mechanisms for communication and language development.

Investigates multi-agent reinforcement learning, emergent communication, and
discrete/continuous representation learning. Training, evaluation and
inference are strictly separated (spec §3 EAL-LEARNING).

A CPU reference implementation is provided so experiments run without NVIDIA
hardware or ML libraries. Production NVIDIA backends (NeMo RL, GRPO, etc.)
implement the same :class:`RLAlgorithm` / :class:`ModelInference` interfaces
and are swapped in behind them; absence of hardware never blocks testing.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from typing import Any, Optional

from eal_brain import Agent, ReferenceLearner
from eal_brain.state import AgentState
from eal_cl import Channel, Encoder, Decoder
from eal_core.config import Config
from eal_core.event_bus import EventBus
from eal_core.experiment import ExperimentRecord, ExperimentResult
from eal_core.identity import AgentIdentity


@dataclass
class Experience:
    """A single learning experience for one agent.

    Attributes:
        agent_id: The agent that had the experience.
        concept: The communicated concept.
        symbols: The symbol sequence used.
        reward: Observed reward (1.0 success, 0.0 failure).
        round: Round index within the experiment.
    """

    agent_id: str
    concept: Any
    symbols: tuple[str, ...]
    reward: float
    round: int


class RLAlgorithm:
    """Strict RL algorithm interface.

    update(agent, experiences) -> metrics
    evaluate(agent, experiences) -> metrics
    """

    def update(self, agent: Agent,
               experiences: list[Experience]) -> dict[str, float]:
        raise NotImplementedError

    def evaluate(self, agent: Agent,
                 experiences: list[Experience]) -> dict[str, float]:
        raise NotImplementedError


class ReferenceRL(RLAlgorithm):
    """Reference reinforcement-learning algorithm (stdlib only).

    Reinforces each agent's encoder/decoder mappings in proportion to the
    observed reward. Deterministic given a seed. Not a production RL algorithm;
    keeps EAL-LEARNING runnable without ML libraries or GPUs. Real algorithms
    (GRPO, PPO, contrastive) implement RLAlgorithm behind this interface.
    """

    def __init__(self, learning_rate: float = 0.1, seed: int = 0) -> None:
        self.learning_rate = learning_rate
        self.seed = seed
        self.updates = 0

    def update(self, agent: Agent,
               experiences: list[Experience]) -> dict[str, float]:
        """Training path: update agent beliefs/encoder from experiences."""
        total_reward = 0.0
        n = 0
        for exp in experiences:
            reward = float(exp.reward)
            total_reward += reward
            n += 1
            agent.encoder.reinforce(exp.concept, exp.symbols, reward)
            agent.decoder.reinforce(exp.symbols, exp.concept, reward)
            agent.learn({"reward": reward, "key": f"comm:{exp.concept}"})
        self.updates += 1
        avg = total_reward / n if n else 0.0
        return {
            "avg_reward": avg,
            "experiences": float(n),
            "updates": float(self.updates),
        }

    def evaluate(self, agent: Agent,
                 experiences: list[Experience]) -> dict[str, float]:
        """Evaluation path: measure without updating agent state."""
        if not experiences:
            return {"success_rate": 0.0, "experiences": 0.0}
        correct = 0
        for exp in experiences:
            guess = agent.decoder.decode(exp.symbols)
            if guess == exp.concept:
                correct += 1
        return {
            "success_rate": correct / len(experiences),
            "experiences": float(len(experiences)),
        }


@dataclass
class MultiAgentLearningResult:
    """Outcome of a multi-agent learning experiment.

    Attributes:
        experiment_id: Content-stable id.
        agents: Number of agents.
        rounds: Number of communication rounds.
        training_success: Success rate measured during training (with updates).
        evaluation_success: Success rate measured on held-out evaluation
            experiences (no updates).
        communication_improvement: evaluation_success minus baseline.
        accepted: Whether the learning hypothesis was accepted.
    """

    experiment_id: str
    agents: int
    rounds: int
    training_success: float
    evaluation_success: float
    communication_improvement: float
    accepted: bool


class MultiAgentLearningLoop:
    """Coordinates multiple independent agents learning to communicate.

    Agents are independent (EAL-BRAIN): each has its own state, memory, encoder
    and decoder. They communicate only through explicit :class:`~eal_cl.Channel`
    instances. Training updates agent state; evaluation measures without
    updating; inference encodes/decodes.

    When an :class:`~eal_core.event_bus.EventBus` is supplied, every real
    message sent/received is published on the bus so the observatory can
    observe it. The loop never lets the observatory influence execution.
    """

    def __init__(self, agents: list[Agent],
                 algorithm: RLAlgorithm | None = None,
                 rng: random.Random | None = None,
                 config: Config | None = None,
                 symbol_pool: list[str] | None = None,
                 bus: Optional[EventBus] = None) -> None:
        self.agents = list(agents)
        self.algorithm = algorithm or ReferenceRL(seed=0)
        self.rng = rng or random.Random()
        self.config = config or Config()
        self.symbol_pool = list(symbol_pool or [f"sym-{i}" for i in range(8)])
        self.bus = bus
        self._experiments: list[ExperimentRecord] = []

    def _pair_channels(self) -> list[tuple[Agent, Agent, Channel]]:
        """Pair up agents with dedicated bidirectional channels."""
        pairs: list[tuple[Agent, Agent, Channel]] = []
        shuffled = list(self.agents)
        self.rng.shuffle(shuffled)
        for i in range(0, len(shuffled) - 1, 2):
            a, b = shuffled[i], shuffled[i + 1]
            pairs.append((a, b, Channel(str(a.identity), str(b.identity))))
        return pairs

    def _publish(self, event_type: str, sender: Agent,
                 receiver: Agent, symbols: tuple[str, ...],
                 concept: Any) -> None:
        if self.bus is None:
            return
        self.bus.publish(
            event_type,
            {
                "sender": str(sender.identity),
                "receiver": str(receiver.identity),
                "symbols": list(symbols),
                "concept": concept,
            },
            source=sender.identity,
        )

    def run_round(self, concepts: list[Any],
                  channel: Channel, sender: Agent, receiver: Agent,
                  training: bool = True) -> bool:
        """One communication round.

        If training=True, both agents reinforce after the outcome.
        Returns whether the receiver decoded correctly.
        """
        concept = self.rng.choice(concepts)
        symbols = sender.encoder.encode(
            concept, available_symbols=self.symbol_pool)
        channel.send(str(sender.identity), symbols, concept)
        self._publish("message.sent", sender, receiver, symbols, concept)
        message = channel.receive(str(receiver.identity))
        if message is None:
            return False
        self._publish("message.received", receiver, sender,
                      message.symbols, message.concept)
        guess = receiver.decoder.decode(message.symbols,
                                        candidate_concepts=concepts)
        correct = guess == concept
        reward = 1.0 if correct else 0.0
        if training:
            sender.encoder.reinforce(concept, symbols, reward)
            receiver.decoder.reinforce(message.symbols, guess, reward)
            sender.learn({"reward": reward, "key": f"comm:{concept}"})
            receiver.learn({"reward": reward, "key": f"comm:{guess}"})
        return correct

    def run_experiment(self, hypothesis: str,
                       rounds: int = 200,
                       concepts: list[Any] | None = None,
                       seed: int = 0) -> MultiAgentLearningResult:
        """Run a reproducible multi-agent learning experiment.

        Training and evaluation are separated: the first fraction of rounds
        trains (updates agent state); the remainder evaluates (no updates).
        """
        rng = random.Random(seed)
        if concepts is None:
            concepts = [f"c-{i}" for i in range(6)]

        # Reset agent learning state for reproducibility.
        for agent in self.agents:
            agent.state = AgentState(agent_id=str(agent.identity))
            agent._encoder = None
            agent._decoder = None

        pairs = self._pair_channels()
        if not pairs:
            result = MultiAgentLearningResult(
                experiment_id=self._exp_id(hypothesis, seed, rounds),
                agents=len(self.agents), rounds=rounds,
                training_success=0.0, evaluation_success=0.0,
                communication_improvement=0.0, accepted=False,
            )
            self._record(hypothesis, seed, result, accepted=False)
            return result

        train_rounds = max(1, int(rounds * 0.7))
        eval_rounds = rounds - train_rounds

        train_successes = 0
        train_total = 0
        for r in range(train_rounds):
            a, b, ch = pairs[r % len(pairs)]
            correct = self.run_round(concepts, ch, a, b, training=True)
            train_successes += int(correct)
            train_total += 1

        # Collect held-out evaluation experiences (no state updates).
        eval_experiences: list[Experience] = []
        eval_successes = 0
        eval_total = 0
        for r in range(eval_rounds):
            a, b, ch = pairs[r % len(pairs)]
            concept = rng.choice(concepts)
            # Reuse the trained convention (stored symbols) rather than
            # re-generating, so the decoder sees symbols it learned.
            symbols = a.encoder.stored_symbols(concept)
            if symbols is None:
                symbols = a.encoder.encode(
                    concept, available_symbols=self.symbol_pool)
            ch.send(str(a.identity), symbols, concept)
            msg = ch.receive(str(b.identity))
            if msg is None:
                continue
            guess = b.decoder.decode(msg.symbols, candidate_concepts=concepts)
            correct = guess == concept
            eval_experiences.append(Experience(
                agent_id=str(b.identity), concept=concept,
                symbols=msg.symbols, reward=float(correct), round=r,
            ))
            eval_successes += int(correct)
            eval_total += 1

        training_success = train_successes / train_total if train_total else 0.0
        evaluation_success = eval_successes / eval_total if eval_total else 0.0

        # Baseline: random guessing among concepts.
        baseline = 1.0 / len(concepts) if concepts else 0.0
        improvement = evaluation_success - baseline
        accepted = improvement > 0.0

        result = MultiAgentLearningResult(
            experiment_id=self._exp_id(hypothesis, seed, rounds),
            agents=len(self.agents), rounds=rounds,
            training_success=training_success,
            evaluation_success=evaluation_success,
            communication_improvement=improvement,
            accepted=accepted,
        )
        self._record(hypothesis, seed, result, accepted=accepted,
                     train_metrics={"success": training_success},
                     eval_metrics={"success": evaluation_success,
                                   "baseline": baseline})
        return result

    # -- internal ---------------------------------------------------------

    def _exp_id(self, hypothesis: str, seed: int, rounds: int) -> str:
        payload = json.dumps(
            {"hypothesis": hypothesis, "seed": seed, "rounds": rounds},
            sort_keys=True,
        ).encode("utf-8")
        return "learn-" + hashlib.sha256(payload).hexdigest()[:32]

    def _record(self, hypothesis: str, seed: int,
                result: MultiAgentLearningResult, accepted: bool,
                train_metrics: dict | None = None,
                eval_metrics: dict | None = None) -> None:
        record = ExperimentRecord(
            experiment_id=result.experiment_id,
            hypothesis=hypothesis,
            config=self.config.with_seed(seed),
            code_version="eal-learning/1.0",
            seed=seed,
            baseline="random guessing (" + str(
                (eval_metrics or {}).get("baseline", 0.0)) + ")",
            results=ExperimentResult(
                learning_speed=result.training_success,
                generalization=result.evaluation_success,
            ),
            limitations="CPU reference RL only; no NVIDIA NeMo RL backend",
            decision="accept" if accepted else "reject",
        )
        self._experiments.append(record.finalize())

    def experiments(self) -> list[ExperimentRecord]:
        return list(self._experiments)
