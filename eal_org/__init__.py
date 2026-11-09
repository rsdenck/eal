"""EAL-ORG: autonomous organization framework.

Public API:
    OrganizationEngine   # departments, teams, agents, roles, hierarchy
    HierarchyManager     # hierarchy tree; cycle/orphan prevention
    RoleManager          # roles and permission assignments
    Department, Team     # organizational groupings
    AgentFactory         # EAL-FACTORY autonomous agent creation cycle
    AgentSpec            # agent creation specification
    AgentLifecycleManager# create/promote/demote/suspend/replace/retire
    Task, TaskDelegationEngine  # EAL-ORCHESTRATOR task delegation
    CommandControlEngine  # command & control: decompose, delegate, track
    AgentPerformanceEvaluator  # performance management
    GovernancePolicyEngine, OrganizationalAuditLog  # security + audit
    OwnerAgent           # EAL-OWNER: executive agent
    WorkerAgent          # EAL-WORKER: autonomous worker
    OrganizationManager  # EAL-MANAGER: management framework

EAL-ORG is an original framework for autonomous agent organization: the
system creates its Owners, Workers, departments, hierarchy, and delegates
tasks itself, respecting governance/security boundaries (external approval
for privileged actions, resource limits, cycle detection, no orphans).

All organizational changes are recorded in an append-only, immutable audit
log for reproducibility and rollback.
"""

from .orchestrator import CommandControlEngine
from .department import Department, Team
from .factory import AgentFactory, AgentSpec, AgentCreationRecord
from .governance import GovernancePolicyEngine, OrganizationalAuditLog
from .hierarchy import HierarchyManager
from .lifecycle import AgentLifecycleManager, LifecycleEvent
from .manager import OrganizationManager
from .organization import OrganizationEngine, OrganizationSnapshot
from .owner import OwnerAgent
from .performance import AgentPerformanceEvaluator, PerformanceReport
from .roles import Role, RoleManager, DEFAULT_ROLES
from .tasks import Task, TaskDelegationEngine
from .worker import WorkerAgent

__all__ = [
    "AgentCreationRecord",
    "AgentFactory",
    "AgentLifecycleManager",
    "AgentPerformanceEvaluator",
    "AgentSpec",
    "CommandControlEngine",
    "Department",
    "HierarchyManager",
    "LifecycleEvent",
    "OrganizationEngine",
    "OrganizationManager",
    "OrganizationSnapshot",
    "OwnerAgent",
    "PerformanceReport",
    "Role",
    "RoleManager",
    "Task",
    "TaskDelegationEngine",
    "Team",
    "WorkerAgent",
    "DEFAULT_ROLES",
    "GovernancePolicyEngine",
    "OrganizationalAuditLog",
]
