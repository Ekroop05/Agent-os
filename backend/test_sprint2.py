"""Quick validation tests for Sprint 2 changes."""

import sys
sys.path.insert(0, ".")

from app.services.workspace_service import workspace_service, slugify, title_case_slug
from app.schemas import WorkspaceCreate

print("=" * 60)
print("SPRINT 2 VALIDATION TESTS")
print("=" * 60)

# ── P1: Slugify Tests ─────────────────────────────────────────
print("\n[P1] Slug Generation:")
tests = [
    ("Superhero Website", "superhero-website"),
    ("Netflix Clone", "netflix-clone"),
    ("AI Resume Analyzer", "ai-resume-analyzer"),
    ("Build an AI Bot", "build-an-ai-bot"),
    ("  spaces  around  ", "spaces-around"),
]
for name, expected in tests:
    result = slugify(name)
    status = "PASS" if result == expected else "FAIL"
    print(f"  [{status}] '{name}' -> '{result}' (expected '{expected}')")

print("\n[P1] Title-Case Slug:")
tests_tc = [
    ("superhero-website", "Superhero-Website"),
    ("netflix-clone", "Netflix-Clone"),
    ("ai-resume-analyzer", "Ai-Resume-Analyzer"),
]
for slug, expected in tests_tc:
    result = title_case_slug(slug)
    status = "PASS" if result == expected else "FAIL"
    print(f"  [{status}] '{slug}' -> '{result}' (expected '{expected}')")

# ── P1/P3: Workspace Creation ─────────────────────────────────
print("\n[P1/P3] Workspace Creation:")
ws1 = workspace_service.create(WorkspaceCreate(
    name="Superhero Website",
    description="A hero site",
    active_agents=1,
))
print(f"  id:           {ws1.id}")
print(f"  project_name: {ws1.project_name}")
print(f"  slug:         {ws1.slug}")
print(f"  path:         {ws1.path}")
print(f"  status:       {ws1.status}")
print(f"  progress:     {ws1.progress}")

assert ws1.project_name == "Superhero Website", f"FAIL: project_name is '{ws1.project_name}'"
assert ws1.slug == "superhero-website", f"FAIL: slug is '{ws1.slug}'"
assert ws1.path == "D:/Projects/Superhero-Website", f"FAIL: path is '{ws1.path}'"
assert ws1.status == "Planning", f"FAIL: status is '{ws1.status}'"
print("  [PASS] All metadata correct")

# ── P2: Duplicate Protection ──────────────────────────────────
print("\n[P2] Duplicate Protection:")
ws2 = workspace_service.create(WorkspaceCreate(
    name="Superhero Website",
    description="A duplicate",
    active_agents=1,
))
print(f"  Duplicate id:   {ws2.id}")
print(f"  Duplicate slug: {ws2.slug}")
print(f"  Duplicate path: {ws2.path}")

assert ws2.id != ws1.id, "FAIL: IDs should be different"
assert "v2" in ws2.slug, f"FAIL: slug should contain 'v2', got '{ws2.slug}'"
assert "v2" in ws2.path.lower(), f"FAIL: path should contain 'v2', got '{ws2.path}'"
print("  [PASS] Duplicate detected and versioned")

# Third duplicate
ws3 = workspace_service.create(WorkspaceCreate(
    name="Superhero Website",
    description="Another dup",
))
print(f"  Triple id:   {ws3.id}")
print(f"  Triple path: {ws3.path}")
assert "v3" in ws3.slug, f"FAIL: expected v3, got '{ws3.slug}'"
assert "v3" in ws3.path.lower(), f"FAIL: expected v3 in path, got '{ws3.path}'"
print("  [PASS] Third duplicate correctly versioned to v3")

# ── P5: Security Validation ───────────────────────────────────
print("\n[P5] Security Validation:")
from app.services.task_service import task_service
from app.schemas import TaskCreate, TaskUpdate

t1 = task_service.create(TaskCreate(
    title="Test Task",
    description="Test",
    assigned_agent="Builder Agent",
    workspace_id=ws1.id,
))

# Mark as Failed
task_service.update(TaskUpdate(id=t1.id, status="Failed"))

# Try to approve — should be downgraded to Rejected
result = task_service.update(TaskUpdate(id=t1.id, security_status="Approved"))
print(f"  Task status: {result.status}")
print(f"  Security status: {result.security_status}")
print(f"  Security notes: {result.security_notes}")
assert result.security_status == "Rejected", f"FAIL: expected Rejected, got '{result.security_status}'"
print("  [PASS] Failed task cannot be Approved")

# Create a completed task and approve it
t2 = task_service.create(TaskCreate(
    title="Completed Task",
    description="Test",
    assigned_agent="Builder Agent",
    workspace_id=ws1.id,
))
task_service.update(TaskUpdate(id=t2.id, status="Completed"))
result2 = task_service.update(TaskUpdate(id=t2.id, security_status="Approved"))
assert result2.security_status == "Approved", f"FAIL: expected Approved, got '{result2.security_status}'"
print("  [PASS] Completed task CAN be Approved")

# ── P7: Status Lifecycle ──────────────────────────────────────
print("\n[P7] Status Lifecycle:")
ws = workspace_service.get(ws1.id)
print(f"  Initial status: {ws.status}")
assert ws.status == "Planning"

workspace_service.update_build_status(ws1.id, "Building", "Builder Agent", "Create Project Folder")
ws = workspace_service.get(ws1.id)
print(f"  After build start: {ws.status}")
assert ws.status == "Building"

workspace_service.update_build_status(ws1.id, "Reviewing", "Security Agent", "Create Project Folder")
ws = workspace_service.get(ws1.id)
print(f"  After security review: {ws.status}")
assert ws.status == "Reviewing"

workspace_service.update(ws1.id, status="Completed", progress=100, current_agent=None, current_task_title=None)
ws = workspace_service.get(ws1.id)
print(f"  After completion: {ws.status}, progress={ws.progress}")
assert ws.status == "Completed"
assert ws.progress == 100
print("  [PASS] Full lifecycle works")

# ── P9: Archive ───────────────────────────────────────────────
print("\n[P9] Workspace Archive:")
workspace_service.archive_workspace(ws)
archive = workspace_service.list_archive()
print(f"  Archive entries: {len(archive)}")
assert len(archive) == 1
assert archive[0].project_name == "Superhero Website"
print(f"  Archived: {archive[0].project_name} — {archive[0].status}")
print("  [PASS] Archive works")

print("\n" + "=" * 60)
print("ALL TESTS PASSED")
print("=" * 60)
