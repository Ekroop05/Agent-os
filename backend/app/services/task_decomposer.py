"""
Task Decomposer — the heart of Sprint M1.

Converts coarse architecture tasks into atomic, builder-friendly micro-tasks
with metadata and dependency ordering.

Decomposition strategies:
  1. Template-based — rule-based expansion for known task patterns
  2. LLM-augmented — for custom/unknown tasks, with template fallback
  3. Dependency graph — topological sort for valid execution order
"""

from __future__ import annotations

import json
import logging
import re
from copy import deepcopy
from typing import Any

logger = logging.getLogger("task_decomposer")


# ── Atomic Task Structure ─────────────────────────────────────────────────

def _task(
    title: str,
    description: str,
    task_type: str,
    expected_output: str,
    dependencies: list[str] | None = None,
    priority: str = "High",
) -> dict:
    """Create a standardised atomic task dict."""
    return {
        "title": title,
        "description": description,
        "type": task_type,
        "expected_output": expected_output,
        "dependencies": dependencies or [],
        "priority": priority,
    }


# ── Planning Tasks (to be filtered) ──────────────────────────────────────

_PLANNING_PATTERNS = [
    r"^define\b",
    r"^design\b",
    r"^gather\b",
    r"^analyze\b",
    r"^analyse\b",
    r"^research\b",
    r"^document\s+(scope|goals|requirements)",
    r"^plan\b",
    r"^scope\b",
    r"^confirm\s+scope",
    r"product\s+scope",
    r"system\s+architecture",
]


def _is_planning_task(title: str) -> bool:
    """Return True if the title represents a planning/architecture task."""
    t = title.strip().lower()
    return any(re.search(p, t) for p in _PLANNING_PATTERNS)


# ── Decomposition Templates ──────────────────────────────────────────────
# Each template is a function(spec) -> list[dict] that returns atomic tasks
# for a given coarse-task pattern.


def _decompose_frontend_shell(spec: dict) -> list[dict]:
    """Decompose 'Build frontend shell' into atomic tasks."""
    frontend = spec.get("frontend", "React + Vite")
    name = spec.get("project_name", "Project")
    theme = spec.get("theme", "General")
    features = spec.get("required_features", [])

    tasks = [
        _task(
            f"Create {frontend} Project",
            f"Initialise the {frontend} project with package.json, vite.config, and entry files for {name}.",
            "frontend",
            "package.json, vite.config.js, index.html, src/main.jsx created",
        ),
        _task(
            "Create Theme Variables and Global Styles",
            f"Create CSS variables for the {theme} theme: color palette, typography, spacing, and breakpoints. "
            f"Create index.css with global resets and base styles.",
            "frontend",
            "src/index.css created with CSS custom properties and global styles",
            dependencies=[f"Create {frontend} Project"],
        ),
        _task(
            "Create Navbar Component",
            f"Create a responsive navigation bar component for {name} with logo area, navigation links, "
            f"and mobile hamburger menu. Use the {theme} theme colors.",
            "frontend",
            "src/components/Navbar.jsx and src/components/Navbar.css created and exported",
            dependencies=["Create Theme Variables and Global Styles"],
        ),
        _task(
            "Create Footer Component",
            f"Create a footer component for {name} with copyright, navigation links, and social media icons. "
            f"Use the {theme} theme colors.",
            "frontend",
            "src/components/Footer.jsx and src/components/Footer.css created and exported",
            dependencies=["Create Theme Variables and Global Styles"],
        ),
    ]

    # Add Hero Section if in features
    if any("hero" in f.lower() for f in features):
        tasks.append(_task(
            "Create Hero Section Component",
            f"Create a hero banner component for {name} with headline, subtext, call-to-action button, "
            f"and visual element. Use the {theme} theme colors and tone.",
            "frontend",
            "src/components/Hero.jsx and src/components/Hero.css created and exported",
            dependencies=["Create Theme Variables and Global Styles"],
        ))

    tasks.append(_task(
        "Create Home Page Layout",
        f"Create the main Home page that assembles Navbar, Hero, content sections, and Footer "
        f"into a complete page layout for {name}.",
        "frontend",
        "src/pages/Home.jsx created, imports and renders all shell components",
        dependencies=["Create Navbar Component", "Create Footer Component"],
    ))

    tasks.append(_task(
        "Create App Shell with Routing",
        f"Set up the main App.jsx with React Router, route definitions for all pages, "
        f"and the base application wrapper for {name}.",
        "frontend",
        "src/App.jsx updated with Router and route configuration",
        dependencies=["Create Home Page Layout"],
    ))

    tasks.append(_task(
        "Implement Responsive Layout",
        f"Add responsive CSS media queries to all components and pages. Ensure mobile, "
        f"tablet, and desktop breakpoints work correctly for {name}.",
        "frontend",
        "All component CSS files updated with @media queries",
        dependencies=["Create App Shell with Routing"],
        priority="Medium",
    ))

    return tasks


def _decompose_frontend_features(spec: dict) -> list[dict]:
    """Decompose feature implementation into per-feature atomic tasks."""
    features = spec.get("required_features", [])
    theme = spec.get("theme", "General")
    name = spec.get("project_name", "Project")
    tasks = []

    # Map features to concrete component tasks
    _feature_map = {
        "hero section": {
            "title": "Create Hero Section Component",
            "desc": f"Create a visually striking hero banner for {name} with headline, description, and CTA.",
            "output": "src/components/Hero.jsx and Hero.css created",
        },
        "about section": {
            "title": "Create About Section Component",
            "desc": f"Create an About section for {name} describing the project, mission, and team.",
            "output": "src/components/About.jsx and About.css created",
        },
        "contact section": {
            "title": "Create Contact Section Component",
            "desc": f"Create a Contact section with a form (name, email, message) and contact details.",
            "output": "src/components/Contact.jsx and Contact.css created",
        },
        "contact form": {
            "title": "Create Contact Form Component",
            "desc": f"Create a styled contact form with validation for name, email, and message fields.",
            "output": "src/components/ContactForm.jsx and ContactForm.css created",
        },
        "navigation": {
            "title": "Create Navigation Component",
            "desc": f"Create navigation with links, logo, and responsive mobile menu for {name}.",
            "output": "src/components/Navbar.jsx and Navbar.css created",
        },
        "footer": {
            "title": "Create Footer Component",
            "desc": f"Create a footer with copyright, links, and social icons for {name}.",
            "output": "src/components/Footer.jsx and Footer.css created",
        },
        "responsive layout": {
            "title": "Implement Responsive Layout",
            "desc": "Add CSS media queries for mobile, tablet, and desktop breakpoints across all components.",
            "output": "All CSS files updated with responsive breakpoints",
        },
        "dashboard": {
            "title": "Create Dashboard Page",
            "desc": f"Create a dashboard page with metrics overview, cards, and data display for {name}.",
            "output": "src/pages/Dashboard.jsx and Dashboard.css created",
        },
        "user interface": {
            "title": "Create Core UI Components",
            "desc": f"Create reusable UI components: Button, Card, Input, Modal for {name}.",
            "output": "src/components/ui/ directory with Button, Card, Input, Modal components",
        },
        "data display": {
            "title": "Create Data Display Component",
            "desc": f"Create a data table/grid component with sorting and filtering for {name}.",
            "output": "src/components/DataTable.jsx and DataTable.css created",
        },
        "settings": {
            "title": "Create Settings Page",
            "desc": f"Create a settings page with preference controls for {name}.",
            "output": "src/pages/Settings.jsx and Settings.css created",
        },
        "search": {
            "title": "Create Search Component",
            "desc": f"Create a search bar with filtering and results display for {name}.",
            "output": "src/components/SearchBar.jsx and SearchBar.css created",
        },
        "features section": {
            "title": "Create Features Section Component",
            "desc": f"Create a features showcase section with icon cards for {name}.",
            "output": "src/components/Features.jsx and Features.css created",
        },
        "call to action": {
            "title": "Create Call To Action Component",
            "desc": f"Create a CTA section with headline, description, and action button for {name}.",
            "output": "src/components/CTA.jsx and CTA.css created",
        },
        "testimonials": {
            "title": "Create Testimonials Component",
            "desc": f"Create a testimonials/reviews carousel or grid for {name}.",
            "output": "src/components/Testimonials.jsx and Testimonials.css created",
        },
        "product catalog": {
            "title": "Create Product Catalog Component",
            "desc": f"Create a product grid with cards showing image, name, price, and action for {name}.",
            "output": "src/components/ProductCatalog.jsx and ProductCatalog.css created",
        },
        "product detail": {
            "title": "Create Product Detail Page",
            "desc": f"Create a product detail page with images, description, pricing, and add-to-cart for {name}.",
            "output": "src/pages/ProductDetail.jsx and ProductDetail.css created",
        },
        "shopping cart": {
            "title": "Create Shopping Cart Component",
            "desc": f"Create a shopping cart with item list, quantities, totals, and checkout button for {name}.",
            "output": "src/components/Cart.jsx and Cart.css created",
        },
        "checkout": {
            "title": "Create Checkout Page",
            "desc": f"Create a checkout page with shipping form, payment summary, and order confirmation for {name}.",
            "output": "src/pages/Checkout.jsx and Checkout.css created",
        },
        "image gallery": {
            "title": "Create Image Gallery Component",
            "desc": f"Create an image gallery with grid layout and lightbox for {name}.",
            "output": "src/components/Gallery.jsx and Gallery.css created",
        },
        "article list": {
            "title": "Create Article List Component",
            "desc": f"Create a blog/article list with cards showing title, excerpt, date for {name}.",
            "output": "src/components/ArticleList.jsx and ArticleList.css created",
        },
        "article detail": {
            "title": "Create Article Detail Page",
            "desc": f"Create an article detail page with full content, author info, and related articles for {name}.",
            "output": "src/pages/ArticleDetail.jsx and ArticleDetail.css created",
        },
        "categories": {
            "title": "Create Categories Component",
            "desc": f"Create a categories sidebar or navigation for content browsing in {name}.",
            "output": "src/components/Categories.jsx and Categories.css created",
        },
        "metrics overview": {
            "title": "Create Metrics Overview Component",
            "desc": f"Create a metrics dashboard with stat cards and trend indicators for {name}.",
            "output": "src/components/MetricsOverview.jsx and MetricsOverview.css created",
        },
        "data tables": {
            "title": "Create Data Tables Component",
            "desc": f"Create sortable, filterable data tables for {name}.",
            "output": "src/components/DataTable.jsx and DataTable.css created",
        },
        "charts": {
            "title": "Create Charts Component",
            "desc": f"Create chart visualisations (bar, line, pie) for {name} dashboard.",
            "output": "src/components/Charts.jsx and Charts.css created",
        },
        "filters": {
            "title": "Create Filter Controls Component",
            "desc": f"Create filter UI with dropdowns, date pickers, and search for {name}.",
            "output": "src/components/Filters.jsx and Filters.css created",
        },
        "projects showcase": {
            "title": "Create Projects Showcase Component",
            "desc": f"Create a portfolio/projects grid with cards, images, and detail links for {name}.",
            "output": "src/components/ProjectsShowcase.jsx and ProjectsShowcase.css created",
        },
        "skills section": {
            "title": "Create Skills Section Component",
            "desc": f"Create a skills display with progress bars or badges for {name}.",
            "output": "src/components/Skills.jsx and Skills.css created",
        },
        "menu section": {
            "title": "Create Menu Section Component",
            "desc": f"Create a menu/catalog section with categories and items for {name}.",
            "output": "src/components/MenuSection.jsx and MenuSection.css created",
        },
    }

    seen = set()
    for feature in features:
        key = feature.lower().strip()
        if key in seen:
            continue
        seen.add(key)

        mapping = _feature_map.get(key)
        if mapping:
            tasks.append(_task(
                mapping["title"],
                mapping["desc"],
                "frontend",
                mapping["output"],
                dependencies=["Create Theme Variables and Global Styles"],
            ))
        else:
            # Generic feature task
            tasks.append(_task(
                f"Implement {feature}",
                f"Create the {feature} feature for {name} with full UI, styling, "
                f"and interactivity matching the {theme} theme.",
                "frontend",
                f"src/components/{feature.replace(' ', '')}.jsx created",
                dependencies=["Create Theme Variables and Global Styles"],
            ))

    return tasks


def _decompose_backend_api(spec: dict) -> list[dict]:
    """Decompose 'Build backend API' into atomic tasks."""
    backend = spec.get("backend", "FastAPI")
    database = spec.get("database", "SQLite")
    name = spec.get("project_name", "Project")
    has_auth = spec.get("authentication") and spec["authentication"] is not False
    has_db = spec.get("database") and spec["database"] is not False

    tasks = [
        _task(
            f"Create {backend} Project",
            f"Initialise the {backend} backend project with main entry point, CORS configuration, "
            f"health endpoint, and requirements file for {name}.",
            "backend",
            "backend/main.py, backend/requirements.txt created",
        ),
    ]

    if has_db:
        tasks.extend([
            _task(
                "Create Database Configuration",
                f"Set up {database} database connection, session management, and base model for {name}.",
                "backend",
                "backend/app/database.py created with engine, session, and Base",
                dependencies=[f"Create {backend} Project"],
            ),
            _task(
                "Create Data Models",
                f"Define SQLAlchemy/ORM models for the core entities of {name}. "
                f"Include fields, relationships, and constraints.",
                "backend",
                "backend/app/models/ directory with model files created",
                dependencies=["Create Database Configuration"],
            ),
            _task(
                "Create Pydantic Schemas",
                f"Create Pydantic request/response schemas for all models in {name}. "
                f"Include Create, Update, and Response variants.",
                "backend",
                "backend/app/schemas/ directory with schema files created",
                dependencies=["Create Data Models"],
            ),
            _task(
                "Create CRUD Service Layer",
                f"Implement CRUD operations (create, read, update, delete) for all models in {name}.",
                "backend",
                "backend/app/services/ directory with CRUD service files created",
                dependencies=["Create Data Models", "Create Pydantic Schemas"],
            ),
            _task(
                "Create List Endpoint",
                f"Create GET endpoint to list/query entities with pagination and filters for {name}.",
                "backend",
                "backend/app/routes/ updated with list endpoint",
                dependencies=["Create CRUD Service Layer"],
            ),
            _task(
                "Create Detail Endpoint",
                f"Create GET endpoint to retrieve a single entity by ID for {name}.",
                "backend",
                "backend/app/routes/ updated with detail endpoint",
                dependencies=["Create CRUD Service Layer"],
            ),
            _task(
                "Create Create Endpoint",
                f"Create POST endpoint to create a new entity for {name}.",
                "backend",
                "backend/app/routes/ updated with create endpoint",
                dependencies=["Create CRUD Service Layer"],
            ),
            _task(
                "Create Update Endpoint",
                f"Create PUT/PATCH endpoint to update an existing entity for {name}.",
                "backend",
                "backend/app/routes/ updated with update endpoint",
                dependencies=["Create CRUD Service Layer"],
            ),
            _task(
                "Create Delete Endpoint",
                f"Create DELETE endpoint to remove an entity for {name}.",
                "backend",
                "backend/app/routes/ updated with delete endpoint",
                dependencies=["Create CRUD Service Layer"],
            ),
        ])
    else:
        tasks.append(_task(
            "Create API Routes",
            f"Create REST API route definitions and handlers for {name}.",
            "backend",
            "backend/app/routes/ directory with route files created",
            dependencies=[f"Create {backend} Project"],
        ))

    if has_auth:
        tasks.extend([
            _task(
                "Create Auth Configuration",
                f"Set up authentication configuration with JWT secret, token expiry, "
                f"and password hashing for {name}.",
                "backend",
                "backend/app/auth/config.py created",
                dependencies=[f"Create {backend} Project"],
            ),
            _task(
                "Create User Model",
                f"Create User model with email, hashed password, and profile fields for {name}.",
                "backend",
                "backend/app/models/user.py created",
                dependencies=["Create Database Configuration"] if has_db else [f"Create {backend} Project"],
            ),
            _task(
                "Create Login Endpoint",
                f"Create POST /auth/login endpoint with credential validation and JWT token response for {name}.",
                "backend",
                "backend/app/routes/auth.py updated with login endpoint",
                dependencies=["Create Auth Configuration", "Create User Model"],
            ),
            _task(
                "Create Register Endpoint",
                f"Create POST /auth/register endpoint with user creation and validation for {name}.",
                "backend",
                "backend/app/routes/auth.py updated with register endpoint",
                dependencies=["Create Auth Configuration", "Create User Model"],
            ),
            _task(
                "Create Auth Middleware",
                f"Create JWT verification middleware and route protection decorator for {name}.",
                "backend",
                "backend/app/auth/middleware.py created",
                dependencies=["Create Auth Configuration"],
            ),
        ])

    return tasks


def _decompose_integration(spec: dict) -> list[dict]:
    """Decompose 'Connect frontend to backend' / 'Integration' tasks."""
    name = spec.get("project_name", "Project")

    return [
        _task(
            "Create API Client Configuration",
            f"Create an Axios/fetch client instance with base URL, default headers, "
            f"and interceptors for {name}.",
            "integration",
            "src/services/apiClient.js created with configured client",
        ),
        _task(
            "Create Service Layer",
            f"Create service modules that wrap API calls for each resource in {name}. "
            f"Each service should export functions for CRUD operations.",
            "integration",
            "src/services/ directory with resource service files created",
            dependencies=["Create API Client Configuration"],
        ),
        _task(
            "Add Loading State Management",
            f"Implement loading state handling across all API-connected components in {name}. "
            f"Add loading spinners and skeleton screens.",
            "frontend",
            "Loading indicators added to all data-fetching components",
            dependencies=["Create Service Layer"],
        ),
        _task(
            "Add Error Handling",
            f"Implement error boundary, API error handling, and user-friendly error messages "
            f"across all components in {name}.",
            "frontend",
            "Error handling and toast/notification system implemented",
            dependencies=["Create Service Layer"],
        ),
    ]


def _decompose_auth_frontend(spec: dict) -> list[dict]:
    """Decompose frontend authentication tasks."""
    name = spec.get("project_name", "Project")
    theme = spec.get("theme", "General")

    return [
        _task(
            "Create Auth Context Provider",
            f"Create a React context for authentication state (user, token, login, logout) for {name}.",
            "frontend",
            "src/context/AuthContext.jsx created and exported",
        ),
        _task(
            "Create Login Page",
            f"Create a login page with email/password form, validation, and error display for {name}. "
            f"Use {theme} theme styling.",
            "frontend",
            "src/pages/Login.jsx and Login.css created",
            dependencies=["Create Auth Context Provider", "Create Theme Variables and Global Styles"],
        ),
        _task(
            "Create Register Page",
            f"Create a registration page with form fields, validation, and success feedback for {name}. "
            f"Use {theme} theme styling.",
            "frontend",
            "src/pages/Register.jsx and Register.css created",
            dependencies=["Create Auth Context Provider", "Create Theme Variables and Global Styles"],
        ),
        _task(
            "Create Protected Route Wrapper",
            f"Create a ProtectedRoute component that redirects unauthenticated users to login for {name}.",
            "frontend",
            "src/components/ProtectedRoute.jsx created and exported",
            dependencies=["Create Auth Context Provider"],
        ),
        _task(
            "Add Auth API Client",
            f"Create auth service module with login, register, logout, and token refresh calls for {name}.",
            "integration",
            "src/services/authService.js created",
            dependencies=["Create Auth Context Provider"],
        ),
    ]


def _decompose_existing_project_edit(spec: dict, edit_description: str) -> list[dict]:
    """Decompose an 'edit existing project' request into atomic tasks."""
    name = spec.get("project_name", "Project")

    # Common edit patterns
    edit_lower = edit_description.lower()

    if "dark mode" in edit_lower or "theme" in edit_lower:
        return [
            _task(
                "Analyze Current Theme",
                f"Review existing CSS variables, colors, and styling approach in {name}.",
                "frontend",
                "Theme analysis complete, existing variables documented",
            ),
            _task(
                "Create Theme Context",
                f"Create a React context for theme switching (light/dark) with localStorage persistence for {name}.",
                "frontend",
                "src/context/ThemeContext.jsx created",
                dependencies=["Analyze Current Theme"],
            ),
            _task(
                "Create Theme Toggle Component",
                f"Create a toggle button/switch component for dark/light mode switching in {name}.",
                "frontend",
                "src/components/ThemeToggle.jsx and ThemeToggle.css created",
                dependencies=["Create Theme Context"],
            ),
            _task(
                "Update CSS Variables for Dark Mode",
                f"Add dark mode CSS custom properties and update existing styles to use "
                f"CSS variables for all colors in {name}.",
                "frontend",
                "index.css updated with [data-theme='dark'] variables",
                dependencies=["Create Theme Context"],
            ),
            _task(
                "Update Navbar with Theme Toggle",
                f"Add the ThemeToggle component to the Navbar in {name}.",
                "frontend",
                "Navbar component updated to include ThemeToggle",
                dependencies=["Create Theme Toggle Component"],
            ),
            _task(
                "Validate Theme Switching",
                f"Ensure all components correctly respond to theme changes in {name}. "
                f"Fix any hardcoded colors.",
                "frontend",
                "All components use CSS variables, theme switching verified",
                dependencies=["Update CSS Variables for Dark Mode", "Update Navbar with Theme Toggle"],
                priority="Medium",
            ),
        ]

    # Generic edit decomposition
    return [
        _task(
            f"Analyze Existing Code for Edit",
            f"Review the current codebase of {name} to understand the scope of: {edit_description}.",
            "frontend",
            "Analysis complete, affected files identified",
        ),
        _task(
            f"Implement {edit_description}",
            f"Apply the requested change to {name}: {edit_description}.",
            "frontend",
            f"Changes applied to {name}",
            dependencies=[f"Analyze Existing Code for Edit"],
        ),
        _task(
            "Validate Changes",
            f"Verify the edit works correctly in {name}. Check for regressions.",
            "frontend",
            "Changes validated, no regressions",
            dependencies=[f"Implement {edit_description}"],
            priority="Medium",
        ),
    ]


def _decompose_polish_deploy(spec: dict) -> list[dict]:
    """Decompose 'Polish and deploy' into atomic tasks."""
    name = spec.get("project_name", "Project")

    return [
        _task(
            "Add Page Transitions and Animations",
            f"Add smooth page transitions, hover effects, and micro-animations to {name}.",
            "frontend",
            "CSS transitions and animations added to components",
            priority="Medium",
        ),
        _task(
            "Add Meta Tags and SEO",
            f"Add proper title, meta description, Open Graph tags, and favicon to {name}.",
            "frontend",
            "index.html updated with meta tags, favicon added",
            priority="Medium",
        ),
        _task(
            "Performance Optimization",
            f"Add lazy loading for images, code splitting for routes, and optimize bundle for {name}.",
            "frontend",
            "Lazy loading and code splitting implemented",
            priority="Low",
        ),
    ]


def _decompose_testing(spec: dict) -> list[dict]:
    """Decompose 'Integration testing' / 'Testing' into atomic tasks."""
    name = spec.get("project_name", "Project")

    return [
        _task(
            "Create Test Configuration",
            f"Set up testing framework (Jest/Vitest) configuration for {name}.",
            "testing",
            "Test config files created, test command works",
        ),
        _task(
            "Create Component Unit Tests",
            f"Write unit tests for core UI components in {name}.",
            "testing",
            "Test files created in __tests__/ or *.test.jsx",
            dependencies=["Create Test Configuration"],
            priority="Medium",
        ),
        _task(
            "Create Integration Tests",
            f"Write integration tests verifying page rendering and navigation in {name}.",
            "testing",
            "Integration test files created and passing",
            dependencies=["Create Test Configuration"],
            priority="Medium",
        ),
    ]


# ── Coarse Task → Template Mapping ────────────────────────────────────────

_TEMPLATE_PATTERNS: list[tuple[list[str], callable]] = [
    # (keyword patterns, decomposition function)
    (["frontend shell", "frontend", "shell", "ui shell", "layout"], _decompose_frontend_shell),
    (["backend api", "backend", "api", "server", "rest api"], _decompose_backend_api),
    (["integration", "connect frontend", "connect front", "frontend to backend"], _decompose_integration),
    (["authentication", "auth", "login", "user auth"], _decompose_auth_frontend),
    (["polish", "deploy", "deployment", "performance", "optimization"], _decompose_polish_deploy),
    (["testing", "test", "integration test", "unit test", "qa"], _decompose_testing),
]


def _match_template(title: str) -> callable | None:
    """Find the best template function for a coarse task title."""
    t = title.strip().lower()
    best_match = None
    best_score = 0

    for patterns, fn in _TEMPLATE_PATTERNS:
        score = sum(1 for p in patterns if p in t)
        if score > best_score:
            best_score = score
            best_match = fn

    return best_match if best_score > 0 else None


# ── LLM-Augmented Decomposition ──────────────────────────────────────────

def _llm_decompose(task_title: str, task_description: str, spec: dict) -> list[dict]:
    """Use LLM to decompose a task that doesn't match any template."""
    from app.services.llm_service import generate_response

    name = spec.get("project_name", "Project")
    theme = spec.get("theme", "General")
    features = ", ".join(spec.get("required_features", []))

    prompt = f"""You are a task decomposition engine. Break the following coarse task into 3-8 ATOMIC micro-tasks.

PROJECT: {name}
THEME: {theme}
FEATURES: {features}

COARSE TASK: {task_title}
DESCRIPTION: {task_description}

Return ONLY valid JSON (no markdown fences) with this structure:
{{
  "tasks": [
    {{
      "title": "Create Specific Component",
      "description": "Detailed description of what to build",
      "type": "frontend|backend|integration|testing",
      "expected_output": "What files/artifacts this produces",
      "dependencies": ["titles of tasks this depends on"],
      "priority": "High|Medium|Low"
    }}
  ]
}}

RULES:
- Every task must be a single, clear implementation objective
- No planning tasks (no "Define", "Analyze", "Research", "Design")
- Each task should produce 1-3 files maximum
- Use descriptive titles like "Create Navbar Component", not "Build Frontend"
- Dependencies reference other task titles in this list
- Do NOT wrap JSON in markdown code fences
- Do NOT include \u003cthink\u003e tags"""

    try:
        import re
        raw = generate_response("qwen3:14b", prompt)
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

        # Extract JSON
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "")
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("No JSON found")

        parsed = json.loads(cleaned[start:end + 1])
        llm_tasks = parsed.get("tasks", [])

        if not llm_tasks:
            raise ValueError("LLM returned empty tasks list")

        # Normalise to our format
        result = []
        for t in llm_tasks:
            result.append(_task(
                title=t.get("title", "Unnamed Task"),
                description=t.get("description", ""),
                task_type=t.get("type", "frontend"),
                expected_output=t.get("expected_output", ""),
                dependencies=t.get("dependencies", []),
                priority=t.get("priority", "High"),
            ))
        return result

    except Exception as e:
        logger.warning("LLM decomposition failed for '%s': %s — using generic fallback", task_title, e)
        return _generic_fallback(task_title, task_description, spec)


def _generic_fallback(task_title: str, task_description: str, spec: dict) -> list[dict]:
    """Last-resort fallback: return the task as-is but cleaned up."""
    name = spec.get("project_name", "Project")
    return [_task(
        title=task_title,
        description=f"{task_description} (for {name})",
        task_type="frontend",
        expected_output=f"Files for {task_title} created",
        priority="High",
    )]


# ── Dependency Graph & Topological Sort ───────────────────────────────────

def _topological_sort(tasks: list[dict]) -> list[dict]:
    """Sort tasks by dependencies. Tasks with no deps come first.

    Falls back to original order if a cycle is detected.
    """
    title_to_task = {t["title"]: t for t in tasks}
    all_titles = set(title_to_task.keys())

    # Build adjacency list (task -> things that depend on it)
    in_degree: dict[str, int] = {title: 0 for title in all_titles}
    dependents: dict[str, list[str]] = {title: [] for title in all_titles}

    for task in tasks:
        for dep in task.get("dependencies", []):
            if dep in all_titles:
                in_degree[task["title"]] += 1
                dependents[dep].append(task["title"])
            # Drop deps referencing tasks not in the list
            # (e.g., from a different decomposition pass)

    # Kahn's algorithm
    queue = [title for title, deg in in_degree.items() if deg == 0]
    sorted_titles: list[str] = []

    while queue:
        # Sort the queue for deterministic output
        queue.sort()
        current = queue.pop(0)
        sorted_titles.append(current)

        for dep_title in dependents.get(current, []):
            in_degree[dep_title] -= 1
            if in_degree[dep_title] == 0:
                queue.append(dep_title)

    if len(sorted_titles) != len(all_titles):
        # Cycle detected — log and fall back to original order
        logger.warning("Dependency cycle detected in task graph — using original order")
        return tasks

    return [title_to_task[t] for t in sorted_titles]


# ── Main Decomposition API ────────────────────────────────────────────────

class TaskDecomposer:
    """Decomposes coarse architecture tasks into atomic micro-tasks."""

    def decompose(
        self,
        architecture_tasks: list[dict],
        spec: dict,
    ) -> list[dict]:
        """Take the raw task_breakdown from architecture and return atomic tasks.

        Parameters
        ----------
        architecture_tasks : list[dict]
            The ``task_breakdown`` array from the architecture JSON.
            Each item has ``title``, ``description``, ``priority``.
        spec : dict
            The project specification from spec_engine.

        Returns
        -------
        list[dict]
            Ordered list of atomic task dicts ready for task_service.create().
        """
        all_atomic: list[dict] = []
        expansion_log: list[dict] = []

        for coarse_task in architecture_tasks:
            title = coarse_task.get("title", "")
            description = coarse_task.get("description", "")

            # Skip planning tasks entirely
            if _is_planning_task(title):
                logger.info("Filtered planning task: %s", title)
                expansion_log.append({
                    "source_task": title,
                    "action": "filtered_planning_task",
                    "expanded_to": [],
                })
                continue

            # Try template-based decomposition first
            template_fn = _match_template(title)
            if template_fn:
                atomic_tasks = template_fn(spec)
                logger.info("Template decomposed '%s' into %d atomic tasks", title, len(atomic_tasks))
            else:
                # LLM-augmented decomposition
                atomic_tasks = _llm_decompose(title, description, spec)
                logger.info("LLM decomposed '%s' into %d atomic tasks", title, len(atomic_tasks))

            expansion_log.append({
                "source_task": title,
                "action": "decomposed",
                "expanded_to": [t["title"] for t in atomic_tasks],
            })

            all_atomic.extend(atomic_tasks)

        # ── Feature-specific tasks ────────────────────────────────────
        # Generate tasks for required features not already covered
        feature_tasks = _decompose_frontend_features(spec)
        existing_titles = {t["title"].lower() for t in all_atomic}
        new_features = [t for t in feature_tasks if t["title"].lower() not in existing_titles]

        if new_features:
            all_atomic.extend(new_features)
            expansion_log.append({
                "source_task": "Required Features (spec)",
                "action": "feature_expansion",
                "expanded_to": [t["title"] for t in new_features],
            })

        # ── Deduplicate ───────────────────────────────────────────────
        seen_titles: set[str] = set()
        deduplicated: list[dict] = []
        for task in all_atomic:
            key = task["title"].strip().lower()
            if key not in seen_titles:
                seen_titles.add(key)
                deduplicated.append(task)

        # ── Topological sort ──────────────────────────────────────────
        sorted_tasks = _topological_sort(deduplicated)

        # ── Clean up dangling dependencies ────────────────────────────
        valid_titles = {t["title"] for t in sorted_tasks}
        for task in sorted_tasks:
            task["dependencies"] = [d for d in task.get("dependencies", []) if d in valid_titles]

        # Store expansion log for task_graph
        self._last_expansion_log = expansion_log

        logger.info(
            "Decomposition complete: %d coarse → %d atomic tasks",
            len(architecture_tasks),
            len(sorted_tasks),
        )

        return sorted_tasks

    @property
    def last_expansion_log(self) -> list[dict]:
        """Return the expansion log from the most recent decompose() call."""
        return getattr(self, "_last_expansion_log", [])


# ── Singleton ─────────────────────────────────────────────────────────────

task_decomposer = TaskDecomposer()
