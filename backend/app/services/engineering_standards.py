"""
Engineering Standards Engine — the source of truth for software engineering best practices.

Initiative 2: Every engineering task produced by the Planner receives
structured engineering standards appropriate to the task type.

The engine:
  - Defines 13 engineering domains (coding, testing, security, etc.)
  - Maintains a registry of Standard Profiles (React, FastAPI, etc.)
  - Resolves the correct profile(s) from the project specification
  - Enriches tasks with standards, deliverables, file expectations
  - Validates enriched tasks via a quality gate

The Builder follows the standards.
Future QA validates against the standards.
Future Editing Mode preserves the standards.
"""

from __future__ import annotations

import logging
import re
from copy import deepcopy
from typing import Any

logger = logging.getLogger("engineering_standards")


# ══════════════════════════════════════════════════════════════════════════════
#  STANDARD DOMAINS
# ══════════════════════════════════════════════════════════════════════════════

STANDARD_DOMAINS = [
    "coding",
    "folder_structure",
    "testing",
    "accessibility",
    "security",
    "performance",
    "documentation",
    "styling",
    "api",
    "database",
    "authentication",
    "deployment",
    "configuration",
]


# ══════════════════════════════════════════════════════════════════════════════
#  STANDARD PROFILES
# ══════════════════════════════════════════════════════════════════════════════
#
#  Each profile is a dict keyed by domain.  Each domain value is a list of
#  concise, actionable rules the Builder must follow.
#
#  The architecture supports future profiles without redesign — just add a
#  new entry to _PROFILE_REGISTRY.
# ══════════════════════════════════════════════════════════════════════════════

_REACT_PROFILE: dict[str, list[str]] = {
    "coding": [
        "Use functional components exclusively — no class components",
        "Use React hooks (useState, useEffect, useContext, useRef) for state and side effects",
        "Create small, reusable, single-responsibility components",
        "No duplicated code — extract shared logic into custom hooks or utility functions",
        "Use clear, descriptive prop names with destructuring in function signatures",
        "Consistent naming: PascalCase for components, camelCase for functions and variables",
        "Use semantic HTML elements (nav, main, section, article, footer, header)",
        "Avoid inline styles — use CSS modules or separate CSS files",
        "Separate container (logic) from presentational (UI) concerns",
        "Export components as named exports alongside default export",
        "Use key props correctly in lists — never use array index as key for dynamic lists",
    ],
    "folder_structure": [
        "src/components/ — reusable UI components (one folder per component with .jsx + .css)",
        "src/pages/ — page-level components mapped to routes",
        "src/context/ — React context providers",
        "src/hooks/ — custom React hooks",
        "src/services/ — API client and service modules",
        "src/utils/ — pure utility functions",
        "src/assets/ — static images, icons, fonts",
        "src/styles/ — global styles and CSS variables",
    ],
    "testing": [
        "Component renders without crashing",
        "No console errors or warnings in output",
        "No build errors — project compiles cleanly",
        "Responsive layout verified at mobile (375px), tablet (768px), and desktop (1024px+)",
        "All interactive elements are clickable and produce expected behavior",
        "Navigation links route to correct pages",
        "Forms validate input before submission",
    ],
    "accessibility": [
        "All interactive elements have ARIA labels or accessible text",
        "Keyboard navigation works for all interactive elements (Tab, Enter, Escape)",
        "Focus is visible on all focusable elements (no outline:none without replacement)",
        "Color contrast meets WCAG AA minimum (4.5:1 for normal text, 3:1 for large text)",
        "Use semantic HTML — headings in order (h1 > h2 > h3), nav, main, footer",
        "Images have descriptive alt text",
        "Form inputs have associated labels",
    ],
    "security": [
        "Never hardcode API keys, secrets, or credentials in source files",
        "Sanitize all user-generated content before rendering (prevent XSS)",
        "Use environment variables for configuration values",
        "Validate all form inputs on the client side before submission",
        "Use HTTPS URLs for all external API calls",
        "No eval() or dangerouslySetInnerHTML unless absolutely necessary with sanitization",
    ],
    "performance": [
        "Use React.lazy() and Suspense for route-based code splitting",
        "Avoid unnecessary re-renders — memoize with React.memo, useMemo, useCallback where appropriate",
        "Lazy load images below the fold",
        "Reuse components instead of duplicating markup",
        "Avoid duplicated state — derive computed values instead of storing them",
        "Minimize bundle size — avoid importing entire libraries when a submodule suffices",
        "Use CSS transitions over JavaScript animations where possible",
    ],
    "documentation": [
        "Add JSDoc comments on component files describing purpose and props",
        "Include prop type documentation (TypeScript types or JSDoc @param)",
        "Add code comments for non-obvious logic only — avoid commenting obvious code",
    ],
    "styling": [
        "Mobile-first responsive design — start with mobile styles, add breakpoints for larger screens",
        "Use CSS custom properties (variables) for all theme colors, spacing, and typography",
        "Use consistent spacing scale (4px, 8px, 12px, 16px, 24px, 32px, 48px, 64px)",
        "No magic numbers — define all repeated values as CSS variables",
        "Use relative units (rem, em, %) over fixed pixels for typography and layout",
        "Separate component styles into co-located .css files (ComponentName.css)",
        "Use BEM or flat naming convention for CSS classes",
    ],
    "api": [
        "Create a centralized API client (axios or fetch wrapper) with base URL configuration",
        "Handle loading, error, and empty states for all API-connected components",
        "Use async/await for API calls — no raw .then() chains",
        "Implement request/response interceptors for auth tokens and error handling",
    ],
    "database": [],  # Frontend does not directly access databases
    "authentication": [
        "Store auth tokens in memory or httpOnly cookies — never in localStorage",
        "Implement a ProtectedRoute wrapper for authenticated routes",
        "Create an AuthContext provider for global auth state",
        "Redirect unauthenticated users to login page",
        "Clear auth state on logout and token expiry",
    ],
    "deployment": [
        "Ensure production build completes without errors (npm run build)",
        "Add proper meta tags (title, description, viewport, Open Graph)",
        "Add favicon and app icons",
        "Configure proper base URL for deployment environment",
    ],
    "configuration": [
        "Use .env files for environment-specific configuration",
        "Prefix environment variables with VITE_ for Vite projects",
        "Do not commit .env files to version control — add to .gitignore",
        "Configure path aliases in vite.config.js for cleaner imports",
    ],
}


_FASTAPI_PROFILE: dict[str, list[str]] = {
    "coding": [
        "Use type hints on all function signatures and return types",
        "Use Pydantic BaseModel for all request/response schemas",
        "Use dependency injection (Depends()) for shared logic (auth, db sessions, etc.)",
        "Proper error handling — raise HTTPException with appropriate status codes",
        "Add structured logging with python logging module",
        "Validate all inputs using Pydantic field validators",
        "Separate business logic into service modules — no business logic in route handlers",
        "Use async def for route handlers when performing I/O operations",
        "Follow single-responsibility principle — one router per resource/domain",
        "Use Enum types for fixed choice fields (status, role, etc.)",
    ],
    "folder_structure": [
        "backend/app/ — main application package",
        "backend/app/routes/ — API route handlers (one file per resource)",
        "backend/app/models/ — SQLAlchemy/ORM model definitions",
        "backend/app/schemas/ — Pydantic request/response schemas",
        "backend/app/services/ — business logic and service layer",
        "backend/app/auth/ — authentication configuration and middleware",
        "backend/app/core/ — configuration, database connection, event bus",
        "backend/app/utils/ — shared utility functions",
        "backend/tests/ — test files mirroring app structure",
    ],
    "testing": [
        "API endpoints return correct HTTP status codes (200, 201, 400, 401, 404, 422)",
        "Response payloads match Pydantic schema definitions",
        "Invalid input returns 422 with validation error details",
        "Unauthorized access returns 401",
        "No unhandled exceptions — all error paths return proper HTTP responses",
        "Database operations are wrapped in transactions",
    ],
    "accessibility": [],  # Backend does not have accessibility concerns
    "security": [
        "Never hardcode secrets, API keys, or database credentials",
        "Validate and sanitize all user inputs via Pydantic models",
        "Sanitize outputs to prevent injection attacks",
        "Apply least-privilege principle — restrict endpoint access by role",
        "Use environment variables for all secrets and configuration",
        "Use safe file handling — validate paths, prevent directory traversal",
        "No eval(), exec(), or os.system() with user-provided input",
        "Configure CORS restrictively — list specific allowed origins",
        "Hash passwords with bcrypt — never store plaintext",
    ],
    "performance": [
        "Use pagination for list endpoints — never return unbounded results",
        "Use database indexes on frequently queried columns",
        "Use connection pooling for database connections",
        "Avoid N+1 query patterns — use eager loading or joinedload",
        "Cache expensive computations where appropriate",
        "Use async I/O for external API calls and file operations",
    ],
    "documentation": [
        "Add docstrings to all route handlers describing purpose, parameters, and responses",
        "Document API endpoints with OpenAPI metadata (summary, description, tags)",
        "Include type annotations that generate accurate Swagger/OpenAPI docs",
        "Add README with setup instructions, environment variables, and API overview",
    ],
    "styling": [],  # Backend does not have styling concerns
    "api": [
        "Use consistent URL patterns: plural nouns for resources (/users, /items)",
        "Use appropriate HTTP methods (GET for read, POST for create, PUT/PATCH for update, DELETE for remove)",
        "Return consistent response shapes across all endpoints",
        "Include pagination metadata in list responses (total, page, per_page)",
        "Use proper HTTP status codes — 201 for created, 204 for deleted, 404 for not found",
        "Version API routes when breaking changes are needed (/api/v1/)",
    ],
    "database": [
        "Define models with proper column types, nullable constraints, and defaults",
        "Use alembic or similar for database migrations — never modify tables manually",
        "Add created_at and updated_at timestamps to all models",
        "Define relationships explicitly with foreign keys and back_populates",
        "Use transactions for multi-step write operations",
        "Index foreign key columns and frequently filtered fields",
    ],
    "authentication": [
        "Use JWT tokens with appropriate expiry (short-lived access, long-lived refresh)",
        "Hash passwords with bcrypt — never store plaintext passwords",
        "Implement token refresh endpoint",
        "Create auth dependency (Depends(get_current_user)) for protected routes",
        "Return 401 for missing/invalid tokens, 403 for insufficient permissions",
        "Log authentication events (login, logout, failed attempts)",
    ],
    "deployment": [
        "Include requirements.txt or pyproject.toml with pinned dependency versions",
        "Add a health check endpoint (GET /health)",
        "Configure logging for production (structured, appropriate level)",
        "Use a production ASGI server (uvicorn with workers)",
        "Add Dockerfile for containerized deployment",
    ],
    "configuration": [
        "Use pydantic Settings class for configuration management",
        "Load configuration from environment variables with sensible defaults",
        "Separate configuration by environment (development, staging, production)",
        "Do not commit .env files — use .env.example as a template",
        "Validate required configuration at startup — fail fast on missing values",
    ],
}


# ══════════════════════════════════════════════════════════════════════════════
#  PROFILE REGISTRY
# ══════════════════════════════════════════════════════════════════════════════

_PROFILE_REGISTRY: dict[str, dict[str, list[str]]] = {
    "react": _REACT_PROFILE,
    "fastapi": _FASTAPI_PROFILE,
    # Future profiles — add here without modifying any other code:
    # "nextjs": _NEXTJS_PROFILE,
    # "vue": _VUE_PROFILE,
    # "node": _NODE_PROFILE,
    # "python_package": _PYTHON_PACKAGE_PROFILE,
    # "flutter": _FLUTTER_PROFILE,
}


# ══════════════════════════════════════════════════════════════════════════════
#  LAYER → RELEVANT DOMAIN MAPPING
# ══════════════════════════════════════════════════════════════════════════════
#
#  Not every domain applies to every task layer.  For example, a frontend
#  task doesn't need database standards, and a backend task doesn't need
#  accessibility standards.  This mapping filters standards to what's relevant.

_LAYER_DOMAINS: dict[str, list[str]] = {
    "FE": ["coding", "folder_structure", "testing", "accessibility", "security",
           "performance", "documentation", "styling", "configuration"],
    "BE": ["coding", "folder_structure", "testing", "security", "performance",
           "documentation", "api", "database", "configuration"],
    "AUTH": ["coding", "testing", "security", "authentication", "documentation"],
    "INT": ["coding", "testing", "security", "api", "performance"],
    "QA": ["testing", "documentation", "configuration"],
    "OPS": ["deployment", "configuration", "performance", "security", "documentation"],
}


# ══════════════════════════════════════════════════════════════════════════════
#  DELIVERABLE INFERENCE
# ══════════════════════════════════════════════════════════════════════════════

def _infer_deliverables(task: dict) -> list[str]:
    """Infer required deliverables from task title and expected_output."""
    deliverables = []
    title = task.get("title", "")
    expected = task.get("expected_output", "")
    combined = f"{title} {expected}".lower()

    # Extract file paths from expected_output
    file_pattern = re.compile(r'((?:src|backend|frontend)/[\w/.-]+\.(?:jsx|js|css|py|json|html|ts|tsx))')
    found_files = file_pattern.findall(expected)
    deliverables.extend(found_files)

    # Infer component deliverables from title
    if "component" in combined or "create" in combined:
        # Extract component name
        component_match = re.search(r'(?:create|implement|add)\s+(\w+(?:\s+\w+)?)\s*(?:component|section|page)?', title, re.IGNORECASE)
        if component_match:
            component_name = component_match.group(1).strip().replace(" ", "")
            if not any(component_name.lower() in d.lower() for d in deliverables):
                task_type = task.get("type", "frontend")
                if task_type == "frontend":
                    deliverables.append(f"src/components/{component_name}.jsx")
                    deliverables.append(f"src/components/{component_name}.css")

    # Infer page deliverables
    if "page" in combined:
        page_match = re.search(r'(?:create|implement|add)\s+(\w+)\s*page', title, re.IGNORECASE)
        if page_match:
            page_name = page_match.group(1).strip()
            if not any(page_name.lower() in d.lower() for d in deliverables):
                deliverables.append(f"src/pages/{page_name}.jsx")
                deliverables.append(f"src/pages/{page_name}.css")

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for d in deliverables:
        if d.lower() not in seen:
            seen.add(d.lower())
            unique.append(d)

    return unique if unique else [task.get("expected_output", "Implementation files")]


def _infer_expected_files(task: dict) -> dict[str, list[str]]:
    """Infer files to create, modify, and read from task metadata."""
    files_create: list[str] = []
    files_modify: list[str] = []
    files_read: list[str] = []

    title = task.get("title", "").lower()
    expected = task.get("expected_output", "")
    estimated_context = task.get("estimated_context", [])

    # Files to read = estimated context
    files_read = list(estimated_context)

    # Extract file paths from expected_output
    file_pattern = re.compile(r'((?:src|backend|frontend)/[\w/.-]+\.(?:jsx|js|css|py|json|html|ts|tsx))')
    found_files = file_pattern.findall(expected)

    # Determine create vs modify from keywords
    if any(k in title for k in ["create", "add", "implement", "set up", "initialise", "initialize"]):
        files_create.extend(found_files)
    elif any(k in title for k in ["update", "modify", "fix", "refactor", "add to"]):
        files_modify.extend(found_files)
    else:
        files_create.extend(found_files)

    return {
        "create": files_create,
        "modify": files_modify,
        "read": files_read,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  TESTING / SECURITY / PERFORMANCE / DOCUMENTATION EXPECTATIONS
# ══════════════════════════════════════════════════════════════════════════════

def _infer_testing_expectations(task: dict, profile_standards: dict[str, list[str]]) -> list[str]:
    """Generate testing expectations specific to this task."""
    expectations = []
    title = task.get("title", "").lower()
    layer = (task.get("engineering_metadata") or {}).get("layer", "FE")

    # Always include base testing standards from profile
    base_testing = profile_standards.get("testing", [])

    if layer == "FE":
        expectations.append("Component renders without errors")
        expectations.append("No console errors in browser developer tools")
        expectations.append("No build errors — project compiles with npm run build")
        if any(k in title for k in ["responsive", "layout", "page", "navbar", "footer", "hero"]):
            expectations.append("Responsive layout verified at 375px, 768px, and 1024px viewports")
        if any(k in title for k in ["form", "input", "contact", "login", "register"]):
            expectations.append("Form validation works for required fields")
            expectations.append("Error states display clearly to the user")
        if any(k in title for k in ["navigation", "routing", "link"]):
            expectations.append("All navigation links route correctly")
    elif layer == "BE":
        expectations.append("API returns expected HTTP status codes")
        expectations.append("Response payload matches schema definition")
        if any(k in title for k in ["endpoint", "route", "api"]):
            expectations.append("Invalid input returns 422 validation error")
            expectations.append("Missing resource returns 404")
    elif layer == "AUTH":
        expectations.append("Unauthorized access is properly restricted")
        expectations.append("Valid credentials produce authentication token")
        expectations.append("Invalid credentials return appropriate error")

    return expectations if expectations else base_testing[:3]


def _infer_security_expectations(task: dict, profile_standards: dict[str, list[str]]) -> list[str]:
    """Generate security expectations specific to this task."""
    expectations = []
    title = task.get("title", "").lower()
    layer = (task.get("engineering_metadata") or {}).get("layer", "FE")

    # Universal security standards
    expectations.append("No hardcoded secrets, API keys, or credentials")
    expectations.append("All user inputs are validated before processing")

    if layer == "FE":
        if any(k in title for k in ["form", "input", "contact", "search"]):
            expectations.append("User input is sanitized before rendering")
        expectations.append("External API calls use HTTPS")
    elif layer == "BE":
        expectations.append("Inputs validated via Pydantic schemas")
        expectations.append("Outputs sanitized to prevent injection")
        if any(k in title for k in ["endpoint", "route", "api"]):
            expectations.append("Appropriate authorization checks on protected endpoints")
    elif layer == "AUTH":
        expectations.append("Passwords hashed with bcrypt — never stored in plaintext")
        expectations.append("JWT tokens have appropriate expiry")
        expectations.append("Failed auth attempts are logged")

    return expectations


def _infer_performance_expectations(task: dict, profile_standards: dict[str, list[str]]) -> list[str]:
    """Generate performance expectations specific to this task."""
    expectations = []
    title = task.get("title", "").lower()
    layer = (task.get("engineering_metadata") or {}).get("layer", "FE")

    if layer == "FE":
        expectations.append("No unnecessary re-renders — components only update when props/state change")
        expectations.append("Reuse components instead of duplicating markup")
        if any(k in title for k in ["image", "gallery", "photo"]):
            expectations.append("Images are lazy-loaded below the fold")
        if any(k in title for k in ["page", "route", "app shell"]):
            expectations.append("Route-based code splitting with React.lazy()")
    elif layer == "BE":
        if any(k in title for k in ["list", "query", "endpoint"]):
            expectations.append("List endpoints use pagination — no unbounded result sets")
        expectations.append("Database queries are efficient — no N+1 patterns")

    return expectations


def _infer_documentation_expectations(task: dict, profile_standards: dict[str, list[str]]) -> list[str]:
    """Generate documentation expectations specific to this task."""
    expectations = []
    title = task.get("title", "").lower()
    layer = (task.get("engineering_metadata") or {}).get("layer", "FE")
    complexity = task.get("complexity", "S")

    if complexity in ("L", "XL"):
        expectations.append("Add inline code comments explaining complex logic")
        if layer == "BE":
            expectations.append("Update API documentation with new endpoints")

    if layer == "FE":
        expectations.append("Add JSDoc comment on component describing purpose and props")
    elif layer == "BE":
        expectations.append("Add docstring to route handler describing purpose and parameters")

    if any(k in title for k in ["configuration", "setup", "project", "initialize"]):
        expectations.append("Update README with setup instructions if applicable")

    return expectations


# ══════════════════════════════════════════════════════════════════════════════
#  ENGINEERING STANDARDS ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class EngineeringStandardsEngine:
    """Central source of engineering standards for Agent OS.

    Responsibilities:
      1. Resolve the correct standard profile(s) from a project specification
      2. Enrich tasks with domain-specific engineering standards
      3. Generate deliverables, file expectations, and testing/security guidance
      4. Validate enriched tasks via a quality gate
    """

    def __init__(self):
        self._profiles: dict[str, dict[str, list[str]]] = deepcopy(_PROFILE_REGISTRY)

    # ── Profile Management ────────────────────────────────────────────────

    def register_profile(self, name: str, profile: dict[str, list[str]]) -> None:
        """Register a new standard profile.

        Parameters
        ----------
        name : str
            Profile identifier (e.g., "nextjs", "vue").
        profile : dict[str, list[str]]
            Mapping of domain → list of standard rules.
        """
        self._profiles[name.lower()] = deepcopy(profile)
        logger.info("Registered engineering standards profile: %s", name)

    def list_profiles(self) -> list[str]:
        """Return names of all registered profiles."""
        return list(self._profiles.keys())

    def get_profile(self, name: str) -> dict[str, list[str]] | None:
        """Return a copy of a profile by name, or None."""
        profile = self._profiles.get(name.lower())
        return deepcopy(profile) if profile else None

    # ── Profile Resolution ────────────────────────────────────────────────

    def resolve_profiles(self, spec: dict) -> list[str]:
        """Determine which standard profiles apply to a project specification.

        Parameters
        ----------
        spec : dict
            The project specification from spec_engine.

        Returns
        -------
        list[str]
            Profile names that apply (e.g., ["react", "fastapi"]).
        """
        profiles: list[str] = []

        frontend = (spec.get("frontend") or "").lower()
        backend = spec.get("backend")

        # Frontend profile resolution
        if "react" in frontend or "vite" in frontend:
            profiles.append("react")
        elif "next" in frontend:
            if "nextjs" in self._profiles:
                profiles.append("nextjs")
            else:
                profiles.append("react")  # Fallback to React standards
        elif "vue" in frontend:
            if "vue" in self._profiles:
                profiles.append("vue")
            else:
                profiles.append("react")  # Fallback

        # Backend profile resolution
        if backend and backend is not False:
            backend_str = str(backend).lower()
            if "fastapi" in backend_str or "python" in backend_str:
                profiles.append("fastapi")
            elif "node" in backend_str or "express" in backend_str:
                if "node" in self._profiles:
                    profiles.append("node")
                else:
                    profiles.append("fastapi")  # Fallback

        # Ensure at least one profile
        if not profiles:
            profiles.append("react")

        return profiles

    # ── Task Enrichment ───────────────────────────────────────────────────

    def enrich_task(self, task: dict, spec: dict) -> dict:
        """Enrich an engineering task with standards, deliverables, and expectations.

        This method is the core of Initiative 2.  It takes a task dict (as produced
        by PlanningEngine or TaskDecomposer) and enriches its `engineering_metadata`
        with structured engineering standards.

        Parameters
        ----------
        task : dict
            The task dict with at minimum: title, description, engineering_metadata.
        spec : dict
            The project specification.

        Returns
        -------
        dict
            The same task dict, mutated in place, with enriched engineering_metadata.
        """
        meta = task.get("engineering_metadata") or {}
        layer = meta.get("layer", "FE")

        # Resolve profiles for this project
        profiles = self.resolve_profiles(spec)

        # Select the profile matching this task's layer
        if layer in ("FE", "INT"):
            profile_name = next((p for p in profiles if p in ("react", "nextjs", "vue")), "react")
        elif layer in ("BE",):
            profile_name = next((p for p in profiles if p in ("fastapi", "node")), "fastapi")
        elif layer == "AUTH":
            # Auth tasks get standards from both profiles if both exist
            fe_profile = next((p for p in profiles if p in ("react", "nextjs", "vue")), None)
            be_profile = next((p for p in profiles if p in ("fastapi", "node")), None)
            profile_name = be_profile or fe_profile or "react"
        else:
            profile_name = profiles[0] if profiles else "react"

        profile = self._profiles.get(profile_name, _REACT_PROFILE)

        # Filter standards to domains relevant to this layer
        relevant_domains = _LAYER_DOMAINS.get(layer, STANDARD_DOMAINS)
        filtered_standards: dict[str, list[str]] = {}
        for domain in relevant_domains:
            rules = profile.get(domain, [])
            if rules:
                filtered_standards[domain] = rules

        # Generate task-specific expectations
        deliverables = _infer_deliverables(task)
        expected_files = _infer_expected_files(task)
        testing_expectations = _infer_testing_expectations(task, profile)
        security_expectations = _infer_security_expectations(task, profile)
        performance_expectations = _infer_performance_expectations(task, profile)
        documentation_expectations = _infer_documentation_expectations(task, profile)

        # Enrich engineering_metadata — preserve existing fields
        meta["engineering_standards"] = filtered_standards
        meta["standards_profile"] = profile_name
        meta["required_deliverables"] = deliverables
        meta["expected_files"] = expected_files
        meta["testing_expectations"] = testing_expectations
        meta["security_expectations"] = security_expectations
        meta["performance_expectations"] = performance_expectations
        meta["documentation_expectations"] = documentation_expectations

        task["engineering_metadata"] = meta

        logger.debug(
            "Enriched task '%s' with %s profile (%d domains, %d deliverables)",
            task.get("title", "?"),
            profile_name,
            len(filtered_standards),
            len(deliverables),
        )

        return task

    # ── Quality Gate ──────────────────────────────────────────────────────

    def validate_enriched_task(self, task: dict) -> list[str]:
        """Validate that an enriched task meets engineering quality standards.

        Returns a list of issues.  An empty list means the task passes.

        Parameters
        ----------
        task : dict
            The enriched task dict.

        Returns
        -------
        list[str]
            List of validation issue descriptions.
        """
        issues: list[str] = []
        title = task.get("title", "Unknown")
        meta = task.get("engineering_metadata") or {}

        # Check 1: Engineering standards exist
        if not meta.get("engineering_standards"):
            issues.append(f"Missing engineering standards: '{title}'")

        # Check 2: Acceptance criteria exist
        ac = task.get("acceptance_criteria", [])
        if not ac:
            issues.append(f"Missing acceptance criteria: '{title}'")

        # Check 3: Deliverables exist
        if not meta.get("required_deliverables"):
            issues.append(f"Missing required deliverables: '{title}'")

        # Check 4: Expected files exist
        expected_files = meta.get("expected_files", {})
        if not expected_files or (not expected_files.get("create") and not expected_files.get("modify")):
            issues.append(f"Missing expected files (create/modify): '{title}'")

        # Check 5: Complexity exists
        if not task.get("complexity"):
            issues.append(f"Missing complexity rating: '{title}'")

        # Check 6: Security guidance exists
        if not meta.get("security_expectations"):
            issues.append(f"Missing security expectations: '{title}'")

        # Check 7: Testing guidance exists
        if not meta.get("testing_expectations"):
            issues.append(f"Missing testing expectations: '{title}'")

        if issues:
            logger.debug("Quality gate issues for '%s': %s", title, issues)

        return issues

    # ── Text Formatting ───────────────────────────────────────────────────

    def format_standards_block(self, task: dict) -> str:
        """Format engineering standards as a readable text block for embedding
        into task descriptions.

        This is consumed by SpecEngine.enrich_task_description() to embed
        standards into the description text that the Builder reads.

        Parameters
        ----------
        task : dict
            The enriched task dict with engineering_metadata.

        Returns
        -------
        str
            Formatted text block, or empty string if no standards.
        """
        meta = task.get("engineering_metadata") or {}
        standards = meta.get("engineering_standards", {})
        profile = meta.get("standards_profile", "unknown")

        if not standards:
            return ""

        lines = [
            "",
            "── Engineering Standards ─────────────────────────────────",
            f"  Profile: {profile.upper()}",
        ]

        for domain, rules in standards.items():
            if rules:
                lines.append(f"  [{domain.upper()}]")
                for rule in rules:
                    lines.append(f"    • {rule}")

        # Add testing expectations
        testing = meta.get("testing_expectations", [])
        if testing:
            lines.append("  [TESTING EXPECTATIONS]")
            for t in testing:
                lines.append(f"    ✓ {t}")

        # Add security expectations
        security = meta.get("security_expectations", [])
        if security:
            lines.append("  [SECURITY EXPECTATIONS]")
            for s in security:
                lines.append(f"    🔒 {s}")

        # Add performance expectations
        performance = meta.get("performance_expectations", [])
        if performance:
            lines.append("  [PERFORMANCE EXPECTATIONS]")
            for p in performance:
                lines.append(f"    ⚡ {p}")

        # Add deliverables
        deliverables = meta.get("required_deliverables", [])
        if deliverables:
            lines.append("  [REQUIRED DELIVERABLES]")
            for d in deliverables:
                lines.append(f"    📄 {d}")

        # Add expected files
        expected_files = meta.get("expected_files", {})
        if expected_files:
            create = expected_files.get("create", [])
            modify = expected_files.get("modify", [])
            if create:
                lines.append("  [FILES TO CREATE]")
                for f in create:
                    lines.append(f"    + {f}")
            if modify:
                lines.append("  [FILES TO MODIFY]")
                for f in modify:
                    lines.append(f"    ~ {f}")

        # Add documentation expectations
        docs = meta.get("documentation_expectations", [])
        if docs:
            lines.append("  [DOCUMENTATION EXPECTATIONS]")
            for d in docs:
                lines.append(f"    📝 {d}")

        lines.append("─────────────────────────────────────────────────────────")

        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
#  SINGLETON
# ══════════════════════════════════════════════════════════════════════════════

engineering_standards_engine = EngineeringStandardsEngine()
