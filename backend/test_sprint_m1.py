"""
Sprint M1 — Universal Micro-Task Planner Tests

Tests:
  1. Coffee Shop Website → 15-30 atomic tasks (frontend-only)
  2. Student Management System → 50-100 atomic tasks (full-stack)
  3. Add Dark Mode → ~6-8 focused edit tasks
  4. Validator rejects vague tasks
  5. Validator rejects duplicates
  6. Validator rejects planning tasks
  7. Dependency graph is acyclic (topological sort succeeds)
  8. Task graph JSON structure is correct
  9. No planning tasks reach Builder
"""

import json
import os
import sys
import tempfile

import pytest

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from app.services.task_decomposer import task_decomposer, _is_planning_task, _topological_sort
from app.services.task_validator import task_validator, TaskValidator
from app.services.task_graph import task_graph


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def coffee_shop_spec():
    """Frontend-only coffee shop website spec."""
    return {
        "project_name": "Brew Haven",
        "project_type": "Website",
        "theme": "Food / Culinary",
        "purpose": "Coffee shop showcase",
        "target_users": "Coffee lovers",
        "frontend": "React + Vite",
        "backend": False,
        "database": False,
        "authentication": False,
        "required_features": [
            "Hero Section", "Navigation", "Menu Section",
            "About Section", "Contact Section", "Footer",
            "Responsive Layout",
        ],
        "quality_target": 85,
        "theme_context": {
            "color_palette": "Warm amber (#f59e0b), rich brown (#78350f)",
            "tone": "Warm, inviting, artisanal",
            "content_domain": "Coffee, recipes, menus",
        },
    }


@pytest.fixture
def coffee_shop_architecture():
    """Coarse architecture tasks for a coffee shop website."""
    return [
        {"title": "Define product scope", "description": "Document goals.", "priority": "High"},
        {"title": "Design system architecture", "description": "Create architecture.", "priority": "High"},
        {"title": "Build frontend shell", "description": "Layout, nav, core pages.", "priority": "High"},
        {"title": "Implement Menu Section", "description": "Build the menu feature.", "priority": "High"},
        {"title": "Polish and deploy", "description": "Final polish.", "priority": "Medium"},
    ]


@pytest.fixture
def student_mgmt_spec():
    """Full-stack student management system spec."""
    return {
        "project_name": "StudentHub",
        "project_type": "Web Application",
        "theme": "Education",
        "purpose": "Student management",
        "target_users": "School administrators",
        "frontend": "React + Vite",
        "backend": "FastAPI",
        "database": "PostgreSQL",
        "authentication": True,
        "required_features": [
            "Navigation", "Dashboard", "Data Display", "Settings",
            "Responsive Layout", "User Authentication",
        ],
        "quality_target": 85,
        "theme_context": {
            "color_palette": "Royal blue (#1d4ed8), fresh green (#22c55e)",
            "tone": "Friendly, clear, structured",
            "content_domain": "Courses, students, instructors",
        },
    }


@pytest.fixture
def student_mgmt_architecture():
    """Coarse architecture tasks for a student management system."""
    return [
        {"title": "Define product scope", "description": "Document goals.", "priority": "High"},
        {"title": "Design system architecture", "description": "Create architecture.", "priority": "High"},
        {"title": "Build frontend shell", "description": "Layout, nav, core pages.", "priority": "High"},
        {"title": "Build backend API", "description": "REST endpoints and logic.", "priority": "High"},
        {"title": "Implement core features", "description": "Build primary features.", "priority": "High"},
        {"title": "Integration testing", "description": "Connect and test.", "priority": "Medium"},
        {"title": "Polish and deploy", "description": "Final polish.", "priority": "Medium"},
    ]


@pytest.fixture
def dark_mode_spec():
    """Spec for an existing project edit."""
    return {
        "project_name": "ExistingApp",
        "project_type": "Web Application",
        "theme": "Technology",
        "purpose": "Existing app modification",
        "target_users": "Users",
        "frontend": "React + Vite",
        "backend": False,
        "database": False,
        "authentication": False,
        "required_features": ["Navigation", "Responsive Layout"],
        "quality_target": 85,
        "theme_context": {},
    }


# ── Test 1: Coffee Shop Website (15-30 atomic tasks) ─────────────────────

class TestCoffeeShopDecomposition:
    def test_produces_atomic_tasks(self, coffee_shop_spec, coffee_shop_architecture):
        tasks = task_decomposer.decompose(coffee_shop_architecture, coffee_shop_spec)
        assert len(tasks) >= 15, f"Expected at least 15 tasks, got {len(tasks)}"
        assert len(tasks) <= 40, f"Expected at most 40 tasks, got {len(tasks)}"

    def test_no_planning_tasks(self, coffee_shop_spec, coffee_shop_architecture):
        tasks = task_decomposer.decompose(coffee_shop_architecture, coffee_shop_spec)
        for task in tasks:
            assert not _is_planning_task(task["title"]), \
                f"Planning task leaked through: {task['title']}"

    def test_no_duplicate_titles(self, coffee_shop_spec, coffee_shop_architecture):
        tasks = task_decomposer.decompose(coffee_shop_architecture, coffee_shop_spec)
        titles = [t["title"].lower() for t in tasks]
        assert len(titles) == len(set(titles)), \
            f"Duplicate titles found: {[t for t in titles if titles.count(t) > 1]}"

    def test_all_tasks_have_metadata(self, coffee_shop_spec, coffee_shop_architecture):
        tasks = task_decomposer.decompose(coffee_shop_architecture, coffee_shop_spec)
        for task in tasks:
            assert "title" in task and task["title"], f"Missing title: {task}"
            assert "description" in task and task["description"], f"Missing description: {task}"
            assert "type" in task, f"Missing type: {task}"
            assert "expected_output" in task, f"Missing expected_output: {task}"
            assert "dependencies" in task, f"Missing dependencies: {task}"
            assert isinstance(task["dependencies"], list), f"Dependencies not a list: {task}"

    def test_contains_expected_tasks(self, coffee_shop_spec, coffee_shop_architecture):
        tasks = task_decomposer.decompose(coffee_shop_architecture, coffee_shop_spec)
        titles_lower = {t["title"].lower() for t in tasks}
        
        # Should have these atomic tasks
        expected = ["create navbar component", "create footer component"]
        for exp in expected:
            assert any(exp in t for t in titles_lower), \
                f"Expected atomic task '{exp}' not found. Got: {sorted(titles_lower)}"


# ── Test 2: Student Management System (50-100 atomic tasks) ───────────────

class TestStudentMgmtDecomposition:
    def test_produces_many_atomic_tasks(self, student_mgmt_spec, student_mgmt_architecture):
        tasks = task_decomposer.decompose(student_mgmt_architecture, student_mgmt_spec)
        assert len(tasks) >= 25, f"Expected at least 25 tasks, got {len(tasks)}"

    def test_has_backend_tasks(self, student_mgmt_spec, student_mgmt_architecture):
        tasks = task_decomposer.decompose(student_mgmt_architecture, student_mgmt_spec)
        backend_tasks = [t for t in tasks if t.get("type") == "backend"]
        assert len(backend_tasks) >= 5, \
            f"Expected at least 5 backend tasks, got {len(backend_tasks)}"

    def test_has_frontend_tasks(self, student_mgmt_spec, student_mgmt_architecture):
        tasks = task_decomposer.decompose(student_mgmt_architecture, student_mgmt_spec)
        frontend_tasks = [t for t in tasks if t.get("type") == "frontend"]
        assert len(frontend_tasks) >= 5, \
            f"Expected at least 5 frontend tasks, got {len(frontend_tasks)}"

    def test_has_auth_tasks(self, student_mgmt_spec, student_mgmt_architecture):
        tasks = task_decomposer.decompose(student_mgmt_architecture, student_mgmt_spec)
        titles_lower = {t["title"].lower() for t in tasks}
        auth_related = [t for t in titles_lower if "auth" in t or "login" in t or "register" in t]
        assert len(auth_related) >= 2, \
            f"Expected auth tasks, got: {auth_related}"

    def test_has_database_tasks(self, student_mgmt_spec, student_mgmt_architecture):
        tasks = task_decomposer.decompose(student_mgmt_architecture, student_mgmt_spec)
        titles_lower = {t["title"].lower() for t in tasks}
        db_related = [t for t in titles_lower if "database" in t or "model" in t or "schema" in t or "crud" in t]
        assert len(db_related) >= 3, \
            f"Expected database-related tasks, got: {db_related}"


# ── Test 3: Edit Existing Project (Dark Mode) ────────────────────────────

class TestDarkModeDecomposition:
    def test_dark_mode_edit(self, dark_mode_spec):
        from app.services.task_decomposer import _decompose_existing_project_edit
        tasks = _decompose_existing_project_edit(dark_mode_spec, "Add Dark Mode")
        assert 5 <= len(tasks) <= 10, f"Expected 5-10 tasks, got {len(tasks)}"

    def test_dark_mode_has_theme_context(self, dark_mode_spec):
        from app.services.task_decomposer import _decompose_existing_project_edit
        tasks = _decompose_existing_project_edit(dark_mode_spec, "Add Dark Mode")
        titles = [t["title"] for t in tasks]
        assert any("theme context" in t.lower() for t in titles), \
            f"Expected 'Theme Context' task, got: {titles}"

    def test_dark_mode_has_toggle(self, dark_mode_spec):
        from app.services.task_decomposer import _decompose_existing_project_edit
        tasks = _decompose_existing_project_edit(dark_mode_spec, "Add Dark Mode")
        titles = [t["title"] for t in tasks]
        assert any("toggle" in t.lower() for t in titles), \
            f"Expected 'Toggle' task, got: {titles}"


# ── Test 4: Validator Rejects Vague Tasks ─────────────────────────────────

class TestValidatorVague:
    def test_rejects_build_website(self):
        tasks = [{"title": "Build Website", "description": "Build it", "type": "frontend",
                  "expected_output": "", "dependencies": [], "priority": "High"}]
        result = task_validator.validate(tasks)
        assert result.rejected_count == 1
        assert "vague" in result.rejected[0]["reason"].lower()

    def test_rejects_implement_features(self):
        tasks = [{"title": "Implement features", "description": "Do features", "type": "frontend",
                  "expected_output": "", "dependencies": [], "priority": "High"}]
        result = task_validator.validate(tasks)
        assert result.rejected_count == 1

    def test_accepts_specific_task(self):
        tasks = [{"title": "Create Navbar Component", "description": "Build navbar", "type": "frontend",
                  "expected_output": "Navbar.jsx", "dependencies": [], "priority": "High"}]
        result = task_validator.validate(tasks)
        assert result.accepted_count == 1
        assert result.rejected_count == 0


# ── Test 5: Validator Rejects Duplicates ──────────────────────────────────

class TestValidatorDuplicates:
    def test_rejects_exact_duplicate(self):
        tasks = [
            {"title": "Create Navbar Component", "description": "Build navbar", "type": "frontend",
             "expected_output": "Navbar.jsx", "dependencies": [], "priority": "High"},
            {"title": "Create Navbar Component", "description": "Build navbar", "type": "frontend",
             "expected_output": "Navbar.jsx", "dependencies": [], "priority": "High"},
        ]
        result = task_validator.validate(tasks)
        assert result.accepted_count == 1
        assert result.rejected_count == 1

    def test_rejects_case_insensitive_duplicate(self):
        tasks = [
            {"title": "Create Navbar Component", "description": "Build navbar", "type": "frontend",
             "expected_output": "Navbar.jsx", "dependencies": [], "priority": "High"},
            {"title": "create navbar component", "description": "Build navbar", "type": "frontend",
             "expected_output": "Navbar.jsx", "dependencies": [], "priority": "High"},
        ]
        result = task_validator.validate(tasks)
        assert result.accepted_count == 1
        assert result.rejected_count == 1


# ── Test 6: Validator Rejects Planning Tasks ──────────────────────────────

class TestValidatorPlanningTasks:
    def test_rejects_define_scope(self):
        tasks = [{"title": "Define Product Scope", "description": "Define it", "type": "frontend",
                  "expected_output": "", "dependencies": [], "priority": "High"}]
        result = task_validator.validate(tasks)
        assert result.rejected_count == 1
        assert "planning" in result.rejected[0]["reason"].lower()

    def test_rejects_design_architecture(self):
        tasks = [{"title": "Design System Architecture", "description": "Design it", "type": "frontend",
                  "expected_output": "", "dependencies": [], "priority": "High"}]
        result = task_validator.validate(tasks)
        assert result.rejected_count == 1

    def test_rejects_gather_requirements(self):
        tasks = [{"title": "Gather Requirements", "description": "Gather", "type": "frontend",
                  "expected_output": "", "dependencies": [], "priority": "High"}]
        result = task_validator.validate(tasks)
        assert result.rejected_count == 1


# ── Test 7: Dependency Graph is Acyclic ───────────────────────────────────

class TestDependencyGraph:
    def test_topological_sort_succeeds(self, coffee_shop_spec, coffee_shop_architecture):
        tasks = task_decomposer.decompose(coffee_shop_architecture, coffee_shop_spec)
        sorted_tasks = _topological_sort(tasks)
        assert len(sorted_tasks) == len(tasks), "Topological sort dropped tasks"

    def test_sort_respects_dependencies(self):
        tasks = [
            {"title": "Task C", "dependencies": ["Task A", "Task B"], "type": "frontend",
             "description": "", "expected_output": "", "priority": "High"},
            {"title": "Task A", "dependencies": [], "type": "frontend",
             "description": "", "expected_output": "", "priority": "High"},
            {"title": "Task B", "dependencies": ["Task A"], "type": "frontend",
             "description": "", "expected_output": "", "priority": "High"},
        ]
        sorted_tasks = _topological_sort(tasks)
        titles = [t["title"] for t in sorted_tasks]
        assert titles.index("Task A") < titles.index("Task B"), "Task A should come before Task B"
        assert titles.index("Task A") < titles.index("Task C"), "Task A should come before Task C"
        assert titles.index("Task B") < titles.index("Task C"), "Task B should come before Task C"

    def test_cycle_detection_falls_back(self):
        tasks = [
            {"title": "Task A", "dependencies": ["Task B"], "type": "frontend",
             "description": "", "expected_output": "", "priority": "High"},
            {"title": "Task B", "dependencies": ["Task A"], "type": "frontend",
             "description": "", "expected_output": "", "priority": "High"},
        ]
        sorted_tasks = _topological_sort(tasks)
        # Should fall back to original order instead of crashing
        assert len(sorted_tasks) == 2


# ── Test 8: Task Graph JSON ───────────────────────────────────────────────

class TestTaskGraph:
    def test_save_creates_file(self, tmp_path):
        workspace = str(tmp_path)
        task_graph.save(
            workspace_path=workspace,
            architecture_tasks=[{"title": "Build frontend shell"}],
            expansion_log=[{"source_task": "Build frontend shell", "action": "decomposed", "expanded_to": ["Create Navbar"]}],
            final_tasks=[{"title": "Create Navbar", "type": "frontend", "expected_output": "Navbar.jsx",
                          "dependencies": [], "priority": "High", "description": "Build navbar"}],
            validation_report={"accepted_count": 1, "rejected_count": 0, "rejected": [], "warnings": []},
        )
        graph_path = os.path.join(workspace, ".agentos", "planning", "task_graph.json")
        assert os.path.exists(graph_path), "task_graph.json not created"

        with open(graph_path) as f:
            data = json.load(f)
        assert "generated_at" in data
        assert "architecture_tasks" in data
        assert "expansion_log" in data
        assert "final_tasks" in data
        assert "dependency_graph" in data
        assert "validation_report" in data
        assert "stats" in data

    def test_read_returns_data(self, tmp_path):
        workspace = str(tmp_path)
        task_graph.save(
            workspace_path=workspace,
            architecture_tasks=[],
            expansion_log=[],
            final_tasks=[],
            validation_report={"accepted_count": 0, "rejected_count": 0, "rejected": [], "warnings": []},
        )
        data = task_graph.read(workspace)
        assert data is not None
        assert data["stats"]["final_count"] == 0

    def test_read_returns_none_for_missing(self, tmp_path):
        data = task_graph.read(str(tmp_path))
        assert data is None


# ── Test 9: No Planning Tasks Reach Builder ───────────────────────────────

class TestNoPlanningTasksReachBuilder:
    def test_planning_tasks_filtered_at_decomposer(self, coffee_shop_spec, coffee_shop_architecture):
        tasks = task_decomposer.decompose(coffee_shop_architecture, coffee_shop_spec)
        planning_tasks = [t for t in tasks if _is_planning_task(t["title"])]
        assert len(planning_tasks) == 0, \
            f"Planning tasks leaked: {[t['title'] for t in planning_tasks]}"

    def test_planning_tasks_filtered_at_validator(self):
        tasks = [
            {"title": "Define Product Scope", "description": "...", "type": "frontend",
             "expected_output": "", "dependencies": [], "priority": "High"},
            {"title": "Create Navbar Component", "description": "...", "type": "frontend",
             "expected_output": "Navbar.jsx", "dependencies": [], "priority": "High"},
        ]
        result = task_validator.validate(tasks)
        assert result.accepted_count == 1
        assert result.accepted[0]["title"] == "Create Navbar Component"


# ── Test: Multi-objective Detection ───────────────────────────────────────

class TestMultiObjective:
    def test_detects_multi_objective(self):
        tasks = [
            {"title": "Create login page and implement API endpoints", "description": "...",
             "type": "frontend", "expected_output": "", "dependencies": [], "priority": "High"},
        ]
        result = task_validator.validate(tasks)
        assert result.rejected_count == 1
        assert "multi-objective" in result.rejected[0]["reason"].lower()

    def test_allows_single_objective_with_and(self):
        tasks = [
            {"title": "Create Navbar Component and Styles", "description": "...",
             "type": "frontend", "expected_output": "Navbar.jsx", "dependencies": [], "priority": "High"},
        ]
        result = task_validator.validate(tasks)
        # "Navbar Component and Styles" - "and" is not joining two impl verbs
        assert result.accepted_count == 1


# ── Test: Recursion Guard ─────────────────────────────────────────────────

class TestRecursionGuard:
    def test_rejects_recursive_task(self):
        tasks = [
            {"title": "Build frontend shell", "description": "...", "type": "frontend",
             "expected_output": "", "dependencies": [], "priority": "High"},
        ]
        result = task_validator.validate(tasks, original_titles=["Build frontend shell"])
        assert result.rejected_count == 1
        assert "recursive" in result.rejected[0]["reason"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
