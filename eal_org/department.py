"""EAL-ORG: departments and teams.

A department groups agents around a functional specialization. Teams are
sub-groups within departments.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Team:
    """A team within a department."""

    team_id: str
    name: str
    members: set[str] = field(default_factory=set)

    def add_member(self, agent_id: str) -> None:
        self.members.add(agent_id)

    def remove_member(self, agent_id: str) -> None:
        self.members.discard(agent_id)


@dataclass
class Department:
    """A department with a functional specialization."""

    dept_id: str
    name: str
    specialization: str
    agents: set[str] = field(default_factory=set)
    teams: dict[str, Team] = field(default_factory=dict)

    def add_agent(self, agent_id: str) -> None:
        self.agents.add(agent_id)

    def remove_agent(self, agent_id: str) -> None:
        self.agents.discard(agent_id)
        for team in self.teams.values():
            team.remove_member(agent_id)

    def add_team(self, team: Team) -> None:
        self.teams[team.team_id] = team

    def remove_team(self, team_id: str) -> None:
        self.teams.pop(team_id, None)
