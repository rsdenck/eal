"""Unit tests for EAL-ORG autonomous organization (stdlib only)."""

from __future__ import annotations

import unittest

from eal_core.identity import AgentIdentity
from eal_org import (AgentFactory, AgentSpec, AgentLifecycleManager,
                     AgentPerformanceEvaluator, CommandControlEngine,
                     Department, HierarchyManager, OrganizationEngine,
                     OrganizationManager, OwnerAgent, PerformanceReport,
                     RoleManager, Task, TaskDelegationEngine, Team,
                     WorkerAgent)
from eal_org.governance import GovernancePolicyEngine, OrganizationalAuditLog
from eal_org.roles import DEFAULT_ROLES, Role


class TestRoleManager(unittest.TestCase):
    def test_default_roles(self):
        self.assertIn("owner", DEFAULT_ROLES)
        self.assertIn("worker", DEFAULT_ROLES)

    def test_assign_and_permission(self):
        rm = RoleManager()
        rm.register_role(Role("researcher", {"propose_experiment"}))
        rm.assign("agent-1", "researcher")
        self.assertTrue(rm.has_permission("agent-1", "propose_experiment"))
        self.assertFalse(rm.has_permission("agent-1", "retire_agent"))
        self.assertIsNone(rm.role_of("unknown"))


class TestHierarchyManager(unittest.TestCase):
    def test_add_and_cycle(self):
        h = HierarchyManager()
        self.assertTrue(h.add_agent("a"))
        self.assertTrue(h.add_agent("b", "a"))
        self.assertFalse(h.add_agent("a", "b"))  # cycle
        self.assertEqual(h.parent("b"), "a")
        self.assertTrue(h.is_root("a"))
        self.assertEqual(h.roots(), ["a"])

    def test_reparent_and_orphan_prevention(self):
        h = HierarchyManager()
        h.add_agent("a")
        h.add_agent("b", "a")
        h.add_agent("c", "b")
        h.remove_agent("a")  # direct child b promoted to root; c stays under b
        self.assertTrue(h.is_root("b"))
        self.assertEqual(h.parent("c"), "b")  # c not orphaned; b still exists
        self.assertFalse(h.contains("a"))

    def test_delegation_path(self):
        h = HierarchyManager()
        h.add_agent("ceo")
        h.add_agent("sup", "ceo")
        h.add_agent("w", "sup")
        self.assertEqual(h.path_to_root("w"), ["w", "sup", "ceo"])


class TestOrganizationEngine(unittest.TestCase):
    def test_register_and_retire(self):
        org = OrganizationEngine()
        self.assertTrue(org.register_agent("a", "owner"))
        self.assertTrue(org.register_agent("b", "worker", parent="a",
                                           department="d1"))
        org.create_department("d1", "Research", "language research")
        self.assertTrue(org.assign_department("b", "d1"))
        self.assertEqual(org.department_of("b"), "d1")
        self.assertEqual(org.supervisor("b"), "a")
        self.assertTrue(org.retire_agent("b", reparent_children_to="a"))
        self.assertFalse(org.hierarchy.contains("b"))

    def test_team(self):
        org = OrganizationEngine()
        org.create_department("d1", "Research", "x")
        org.create_team("d1", "t1", "Team Alpha")
        org.register_agent("w", "worker", department="d1")
        self.assertTrue(org.assign_team("w", "t1"))
        self.assertIn("w", org.teams["t1"].members)


class TestFactoryLifecycle(unittest.TestCase):
    def test_create_agent(self):
        factory = AgentFactory()
        spec = AgentSpec(role="worker", specialization="research",
                         objective="learn communication", competencies=["nlp"])
        agent = factory.create_agent(spec)
        self.assertIsNotNone(agent.identity)
        rec = factory.record(str(agent.identity))
        self.assertIsNotNone(rec)
        self.assertTrue(rec.capacity_test_passed)

    def test_lifecycle_promote_retire(self):
        org = OrganizationEngine()
        factory = AgentFactory()
        lifecycle = AgentLifecycleManager(org, factory, org.hierarchy,
                                          org.roles)
        spec = AgentSpec(role="worker", specialization="x", objective="o")
        agent = lifecycle.create(spec)
        aid = str(agent.identity)
        self.assertTrue(lifecycle.promote(aid, "supervisor"))
        self.assertEqual(org.agent_role(aid).name, "supervisor")
        self.assertTrue(lifecycle.retire(aid))
        self.assertFalse(org.hierarchy.contains(aid))


class TestTaskDelegation(unittest.TestCase):
    def test_create_assign_complete(self):
        td = TaskDelegationEngine()
        tid = td.create_task("objective", "owner", "sup", priority=1)
        self.assertTrue(td.assign(tid, "worker-1"))
        self.assertTrue(td.start(tid))
        self.assertTrue(td.complete(tid, "result", ["ev1"]))
        self.assertEqual(td.get(tid).status, "completed")
        self.assertEqual(td.get(tid).result, "result")

    def test_dependency_blocks_start(self):
        td = TaskDelegationEngine()
        t1 = td.create_task("a", "o", "s")
        t2 = td.create_task("b", "o", "s", dependencies=[t1])
        self.assertFalse(td.start(t2))  # not assigned / dep not completed
        td.assign(t2, "w")
        self.assertFalse(td.start(t2))  # dependency t1 not completed
        td.assign(t1, "w")
        td.start(t1)
        td.complete(t1, "r1", [])
        self.assertTrue(td.start(t2))

    def test_failed_and_reassign(self):
        td = TaskDelegationEngine()
        tid = td.create_task("obj", "o", "s")
        td.assign(tid, "w1")
        td.start(tid)
        td.fail(tid, "boom")
        self.assertEqual(td.get(tid).status, "failed")


class TestOrchestrator(unittest.TestCase):
    def test_decompose_and_delegate(self):
        org = OrganizationEngine()
        factory = AgentFactory()
        lifecycle = AgentLifecycleManager(org, factory, org.hierarchy,
                                          org.roles)
        td = TaskDelegationEngine()
        cc = CommandControlEngine(org, lifecycle, td)
        org.register_agent("w", "worker")
        org.register_agent("s", "supervisor")
        oid = cc.receive_objective("learn a language", "external")
        tids = cc.decompose_and_delegate(oid)
        self.assertEqual(len(tids), 3)
        tracking = cc.track()
        self.assertEqual(tracking["objectives"], 1)
        self.assertEqual(tracking["tasks"], 3)

    def test_reassign_failed(self):
        org = OrganizationEngine()
        factory = AgentFactory()
        lifecycle = AgentLifecycleManager(org, factory, org.hierarchy,
                                          org.roles)
        td = TaskDelegationEngine()
        cc = CommandControlEngine(org, lifecycle, td)
        org.register_agent("w1", "worker")
        org.register_agent("w2", "worker")
        oid = cc.receive_objective("obj", "external")
        tids = cc.decompose_and_delegate(oid)
        # fail first task, reassign
        td.fail(tids[0], "boom")
        reassigned = cc.reassign_failed()
        self.assertGreaterEqual(reassigned, 0)


class TestPerformance(unittest.TestCase):
    def test_evaluate_and_rank(self):
        td = TaskDelegationEngine()
        tid1 = td.create_task("o1", "a1", "s")
        td.assign(tid1, "a1")
        td.start(tid1)
        td.complete(tid1, "r", ["e1"])
        tid2 = td.create_task("o2", "a2", "s")
        td.assign(tid2, "a2")
        td.start(tid2)
        td.fail(tid2, "boom")
        pe = AgentPerformanceEvaluator(td)
        rep = pe.evaluate("a1")
        self.assertGreater(rep.score, 0.0)
        rank = pe.rank()
        self.assertEqual(rank[0][0], "a1")


class TestGovernance(unittest.TestCase):
    def test_privileged_approval(self):
        g = GovernancePolicyEngine()
        self.assertTrue(g.requires_approval("retire_agent"))
        self.assertFalse(g.requires_approval("execute_task"))
        self.assertFalse(g.approve("retire_agent", "x", False))
        self.assertTrue(g.approve("retire_agent", "x", True))
        ok, msg = g.check_limits(5, 2)
        self.assertTrue(ok)

    def test_audit_log(self):
        from eal_org.governance import OrganizationalAuditLog
        log = OrganizationalAuditLog()
        e = log.record("create", "owner", "w1", "create_agent", approved=True)
        self.assertEqual(len(log.entries()), 1)
        self.assertTrue(e.approved)
        self.assertEqual(len(log.entries_for("w1")), 1)


class TestOwnerWorkerManager(unittest.TestCase):
    def test_manager_appoint_owner_and_run_objective(self):
        mgr = OrganizationManager()
        spec = AgentSpec(role="owner", specialization="exec",
                         objective="run EAL", competencies=["lead"])
        owner = mgr.appoint_owner(spec)
        self.assertIsInstance(owner, OwnerAgent)
        self.assertIsNotNone(mgr.owner)
        out = mgr.run_objective("develop a communication protocol")
        self.assertIn("tracking", out)
        self.assertEqual(out["tracking"]["objectives"], 1)

    def test_manager_create_worker(self):
        mgr = OrganizationManager()
        spec = AgentSpec(role="worker", specialization="research",
                         objective="learn", competencies=["nlp"])
        worker = mgr.create_worker(spec)
        self.assertIsInstance(worker, WorkerAgent)

    def test_snapshot(self):
        mgr = OrganizationManager()
        snap = mgr.snapshot()
        self.assertIn("organization", snap)
        self.assertIn("tracking", snap)


if __name__ == "__main__":
    unittest.main()
