"""Test script for Engineering Standards Engine (Initiative 2)."""

import json
import sys
sys.path.insert(0, ".")

from app.services.engineering_standards import engineering_standards_engine

passed = 0
failed = 0

def check(label, condition):
    global passed, failed
    if condition:
        print(f"  PASS: {label}")
        passed += 1
    else:
        print(f"  FAIL: {label}")
        failed += 1


# ── Test 1: Frontend task enrichment ──────────────────────────────────────
print("\n=== Test 1: Frontend Task Enrichment ===")

spec = {"project_name": "TestApp", "frontend": "React + Vite", "backend": False}
task = {
    "title": "Create Navbar Component",
    "description": "Create responsive navbar",
    "expected_output": "src/components/Navbar.jsx and src/components/Navbar.css created",
    "acceptance_criteria": ["Component renders", "Responsive"],
    "complexity": "S",
    "estimated_context": ["spec.json", "src/App.jsx"],
    "engineering_metadata": {"layer": "FE", "estimated_files_count": 2, "risk_level": "Low"},
}

enriched = engineering_standards_engine.enrich_task(task, spec)
meta = enriched["engineering_metadata"]

check("Profile is react", meta["standards_profile"] == "react")
check("Has engineering_standards", bool(meta.get("engineering_standards")))
check("Has coding domain", "coding" in meta["engineering_standards"])
check("Has testing domain", "testing" in meta["engineering_standards"])
check("Has accessibility domain", "accessibility" in meta["engineering_standards"])
check("Has security domain", "security" in meta["engineering_standards"])
check("No database domain (frontend)", "database" not in meta["engineering_standards"])
check("Has required_deliverables", bool(meta.get("required_deliverables")))
check("Has expected_files", bool(meta.get("expected_files")))
check("Has testing_expectations", bool(meta.get("testing_expectations")))
check("Has security_expectations", bool(meta.get("security_expectations")))
check("Has performance_expectations", bool(meta.get("performance_expectations")))
check("Has documentation_expectations", bool(meta.get("documentation_expectations")))
check("Preserves existing layer", meta["layer"] == "FE")
check("Preserves existing risk_level", meta["risk_level"] == "Low")
check("Preserves existing estimated_files_count", meta["estimated_files_count"] == 2)


# ── Test 2: Backend task enrichment ───────────────────────────────────────
print("\n=== Test 2: Backend Task Enrichment ===")

spec2 = {"project_name": "TestApp", "frontend": "React + Vite", "backend": "FastAPI"}
task2 = {
    "title": "Create List Endpoint",
    "description": "Create GET endpoint for users",
    "expected_output": "backend/app/routes/ updated with list endpoint",
    "acceptance_criteria": ["Returns 200"],
    "complexity": "M",
    "estimated_context": ["spec.json"],
    "engineering_metadata": {"layer": "BE", "estimated_files_count": 1, "risk_level": "High"},
}

enriched2 = engineering_standards_engine.enrich_task(task2, spec2)
meta2 = enriched2["engineering_metadata"]

check("Profile is fastapi", meta2["standards_profile"] == "fastapi")
check("Has coding domain", "coding" in meta2["engineering_standards"])
check("Has api domain", "api" in meta2["engineering_standards"])
check("Has database domain (backend)", "database" in meta2["engineering_standards"])
check("No accessibility domain (backend)", "accessibility" not in meta2["engineering_standards"])
check("No styling domain (backend)", "styling" not in meta2["engineering_standards"])
check("Has security expectations", bool(meta2.get("security_expectations")))
check("Has testing expectations", bool(meta2.get("testing_expectations")))


# ── Test 3: Auth task enrichment ──────────────────────────────────────────
print("\n=== Test 3: Auth Task Enrichment ===")

task3 = {
    "title": "Create Login Endpoint",
    "description": "Create POST /auth/login",
    "expected_output": "backend/app/routes/auth.py created",
    "acceptance_criteria": ["Login works"],
    "complexity": "M",
    "estimated_context": ["spec.json"],
    "engineering_metadata": {"layer": "AUTH", "estimated_files_count": 1, "risk_level": "High"},
}

enriched3 = engineering_standards_engine.enrich_task(task3, spec2)
meta3 = enriched3["engineering_metadata"]

check("Has authentication domain", "authentication" in meta3["engineering_standards"])
check("Has security domain", "security" in meta3["engineering_standards"])
check("Security mentions password hashing", any("password" in s.lower() or "hash" in s.lower() for s in meta3.get("security_expectations", [])))


# ── Test 4: Quality gate ─────────────────────────────────────────────────
print("\n=== Test 4: Quality Gate ===")

issues_good = engineering_standards_engine.validate_enriched_task(enriched)
check("Enriched task passes quality gate (0 issues)", len(issues_good) == 0)

bad_task = {"title": "Bad Task", "engineering_metadata": {}}
issues_bad = engineering_standards_engine.validate_enriched_task(bad_task)
check("Bare task fails quality gate (has issues)", len(issues_bad) > 0)
check("Reports missing standards", any("engineering standards" in i.lower() for i in issues_bad))
check("Reports missing deliverables", any("deliverables" in i.lower() for i in issues_bad))


# ── Test 5: Standards text block ──────────────────────────────────────────
print("\n=== Test 5: Standards Text Block ===")

block = engineering_standards_engine.format_standards_block(enriched)
check("Block is non-empty", len(block) > 100)
check("Contains CODING section", "[CODING]" in block)
check("Contains TESTING EXPECTATIONS", "[TESTING EXPECTATIONS]" in block)
check("Contains SECURITY EXPECTATIONS", "[SECURITY EXPECTATIONS]" in block)
check("Contains REQUIRED DELIVERABLES", "[REQUIRED DELIVERABLES]" in block)
check("Contains profile name", "REACT" in block)


# ── Test 6: Profile resolution ────────────────────────────────────────────
print("\n=== Test 6: Profile Resolution ===")

profiles1 = engineering_standards_engine.resolve_profiles({"frontend": "React + Vite", "backend": False})
check("React-only project resolves to ['react']", profiles1 == ["react"])

profiles2 = engineering_standards_engine.resolve_profiles({"frontend": "React + Vite", "backend": "FastAPI"})
check("Full-stack resolves to ['react', 'fastapi']", profiles2 == ["react", "fastapi"])

profiles3 = engineering_standards_engine.resolve_profiles({"frontend": "", "backend": False})
check("Empty spec defaults to ['react']", profiles3 == ["react"])


# ── Test 7: Profile management ────────────────────────────────────────────
print("\n=== Test 7: Profile Management ===")

check("Lists 2 profiles", len(engineering_standards_engine.list_profiles()) == 2)

react_profile = engineering_standards_engine.get_profile("react")
check("Can get react profile", react_profile is not None)
check("React profile has coding domain", "coding" in react_profile)

check("Unknown profile returns None", engineering_standards_engine.get_profile("unknown") is None)


# ── Test 8: PlanningEngine integration ────────────────────────────────────
print("\n=== Test 8: PlanningEngine Integration ===")

from app.services.planning_engine import planning_engine

arch_tasks = [
    {"title": "Build frontend shell", "description": "Create the UI", "priority": "High"},
    {"title": "Build backend API", "description": "Create the API", "priority": "High"},
]

enriched_coarse = planning_engine.plan(arch_tasks, spec2)
check("Planning returns enriched tasks", len(enriched_coarse) == 2)

fe_task = enriched_coarse[0]
fe_meta = fe_task.get("engineering_metadata", {})
check("FE task has engineering_standards", bool(fe_meta.get("engineering_standards")))
check("FE task has standards_profile", bool(fe_meta.get("standards_profile")))
check("FE task has required_deliverables", bool(fe_meta.get("required_deliverables")))

be_task = enriched_coarse[1]
be_meta = be_task.get("engineering_metadata", {})
check("BE task has engineering_standards", bool(be_meta.get("engineering_standards")))
check("BE task has standards_profile", bool(be_meta.get("standards_profile")))


# ── Test 9: SpecEngine integration ────────────────────────────────────────
print("\n=== Test 9: SpecEngine Integration ===")

from app.services.spec_engine import spec_engine

desc = spec_engine.enrich_task_description(
    "Create Navbar Component",
    "Create a responsive navbar",
    spec,
    acceptance_criteria=["Component renders"],
    task_uid="TASK-FE-001",
    engineering_metadata=meta,
)
check("Description contains standards block", "Engineering Standards" in desc)
check("Description contains profile name", "REACT" in desc)
check("Description still contains project context", "Project Context" in desc)
check("Description still contains acceptance criteria", "Acceptance Criteria" in desc)

# Test backward compatibility (no engineering_metadata)
desc_old = spec_engine.enrich_task_description(
    "Create Navbar", "Create navbar", spec,
    acceptance_criteria=["Works"], task_uid="TASK-FE-001",
)
check("Backward compatible (no engineering_metadata)", "Project Context" in desc_old)
check("No standards block when metadata absent", "Engineering Standards" not in desc_old)


# ── Test 10: TaskValidator integration ────────────────────────────────────
print("\n=== Test 10: TaskValidator Integration ===")

from app.services.task_validator import task_validator

# Task without standards should produce warnings
tasks_no_standards = [
    {"title": "Create Something Component", "complexity": "S", "engineering_metadata": {}}
]
result = task_validator.validate(tasks_no_standards)
check("Task accepted (not rejected)", result.accepted_count == 1)
check("Warnings include missing standards", any("engineering standards" in w.lower() for w in result.warnings))

# Task with standards should have fewer warnings
tasks_with_standards = [enriched]
result2 = task_validator.validate(tasks_with_standards)
check("Enriched task accepted", result2.accepted_count == 1)
check("No standards-related warnings for enriched task", not any("engineering standards" in w.lower() for w in result2.warnings))


# ── Summary ───────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
    sys.exit(1)
