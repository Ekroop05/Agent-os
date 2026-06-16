"""
Builder Agent Service — executes tasks by generating files and code.

Uses Qwen2.5-Coder 7B via Ollama.
Processes tasks sequentially for a workspace.
Communicates status through the event bus.
Falls back to project templates when LLM is unavailable.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime

logger = logging.getLogger("builder_service")

from app.core.event_bus import event_bus
from app.schemas import Event, TaskUpdate
from app.services.llm_service import generate_response
from app.services.time_service import now_label
from app.services.path_security import validate_write_path, SecurityViolationError

BUILDER_MODEL = "qwen2.5-coder:7b"

# ── Project Templates ─────────────────────────────────────────────────────
# When the LLM is unavailable, the builder uses these templates to create
# proper project structure files instead of documentation stubs.

FRONTEND_TEMPLATE = {
    "frontend/package.json": lambda name, **kw: json.dumps({
        "name": name.lower().replace(" ", "-"),
        "version": "0.1.0",
        "private": True,
        "scripts": {
            "dev": "vite",
            "build": "vite build",
            "preview": "vite preview"
        },
        "dependencies": {
            "react": "^18.2.0",
            "react-dom": "^18.2.0"
        },
        "devDependencies": {
            "@vitejs/plugin-react": "^4.2.0",
            "vite": "^5.0.0"
        }
    }, indent=2),

    "frontend/index.html": lambda name, **kw: f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{name}</title>
</head>
<body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
</body>
</html>
""",

    "frontend/vite.config.js": lambda **kw: """import {{ defineConfig }} from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({{
  plugins: [react()],
  server: {{ port: 3000 }}
}})
""",

    "frontend/src/main.jsx": lambda **kw: """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
""",

    "frontend/src/App.jsx": lambda name, **kw: f"""import React from 'react'

export default function App() {{
  return (
    <div className="app">
      <header className="app-header">
        <h1>{name}</h1>
        <p>Discover everything about {name}. Your journey starts here.</p>
      </header>
      <main className="app-main">
        <section className="hero">
          <h2>Welcome</h2>
          <p>Explore our curated experience designed just for you.</p>
        </section>
      </main>
    </div>
  )
}}
""",

    "frontend/src/index.css": lambda name, **kw: """* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
  background: #0f172a;
  color: #e2e8f0;
  min-height: 100vh;
}

.app-header {
  text-align: center;
  padding: 3rem 1rem;
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
}

.app-header h1 {
  font-size: 2.5rem;
  background: linear-gradient(135deg, #38bdf8, #818cf8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.app-main {
  max-width: 960px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.hero {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 12px;
  padding: 2rem;
  margin-top: 2rem;
}

.hero h2 {
  margin-bottom: 1rem;
  color: #94a3b8;
}

code {
  background: rgba(56, 189, 248, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  color: #7dd3fc;
}
""",

    "frontend/public/.gitkeep": lambda **kw: "",
}

BACKEND_TEMPLATE = {
    "backend/requirements.txt": lambda **kw: """fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.5.0
python-dotenv>=1.0.0
requests>=2.31.0
""",

    "backend/main.py": lambda name, **kw: f"""\"\"\"
{name} — Backend API
\"\"\"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="{name} API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {{"message": "Welcome to {name} API", "status": "running"}}


@app.get("/health")
def health():
    return {{"status": "healthy"}}
""",

    "backend/app/__init__.py": lambda **kw: "# App package\n",

    "backend/app/routes/__init__.py": lambda **kw: "# Routes package\n",

    "backend/app/models/__init__.py": lambda **kw: "# Models package\n",
}

FEATURE_TEMPLATE = {
    "frontend/src/components/.gitkeep": lambda **kw: "",
    "frontend/src/pages/.gitkeep": lambda **kw: "",
    "frontend/src/services/.gitkeep": lambda **kw: "",
}


# ── Task type detection keywords ──────────────────────────────────────────

_FRONTEND_KEYWORDS = ["frontend", "ui", "interface", "shell", "component", "page", "css", "react", "layout"]
_BACKEND_KEYWORDS = ["backend", "api", "server", "endpoint", "route", "database", "model", "service"]
_FEATURE_KEYWORDS = ["feature", "implement", "core"]


class BuilderService:
    """Executes individual build tasks."""

    # ── Public API ────────────────────────────────────────────────────────

    async def execute_task(self, task_id: str, workspace_id: str, architecture: dict | None = None) -> dict:
        """Execute a single task: update status, generate output, create files."""
        from app.services.task_service import task_service
        from app.services.workspace_service import workspace_service
        from app.services.agent_service import agent_service
        from app.services.execution_logger import execution_logger

        task = task_service.get(task_id)
        workspace = workspace_service.get(workspace_id)

        # Update agent status
        agent_service.update("builder-agent", status="Running", current_task=task.title)

        # Mark task as Assigned first, then Running
        task = task_service.update(TaskUpdate(
            id=task_id,
            status="Assigned",
            assigned_agent="Builder Agent",
        ))

        await event_bus.publish(Event(
            type="BUILD_TASK_STARTED",
            source="Builder Agent",
            message=f"Builder assigned: {task.title}",
            severity="info",
            payload={"task_id": task_id, "workspace_id": workspace_id, "title": task.title},
        ))

        # Transition to Running
        task = task_service.update(TaskUpdate(
            id=task_id,
            status="Running",
        ))

        execution_logger.log(workspace.path, "Builder Agent", "TASK_STARTED", task_id, task.title)

        # Update workspace current status
        workspace_service.update_build_status(workspace_id, "Building", "Builder Agent", task.title)

        try:
            # Route to specialized handlers or generic LLM handler
            title_lower = task.title.lower()
            output_files = []

            if "create project folder" in title_lower or "project folder" in title_lower:
                output_files = await self._create_project_folder(workspace)
            elif "base structure" in title_lower or "create base" in title_lower or "folder structure" in title_lower:
                output_files = await self._create_base_structure(workspace)
            elif "readme" in title_lower:
                output_files = await self._create_readme(workspace, architecture)
            elif "manifest" in title_lower or "project.json" in title_lower:
                output_files = await self._create_manifest(workspace, architecture)
            else:
                output_files = await self._generate_for_task(task, workspace, architecture)

            # Log each created file
            for fpath in output_files:
                execution_logger.log(workspace.path, "Builder Agent", "FILE_CREATED", task_id, fpath)

            # ── Sprint 3: Build Validation Layer ────────────────────────
            if not ("create project folder" in title_lower or "base structure" in title_lower or "readme" in title_lower or "manifest" in title_lower):
                validation_errors = self._validate_build_output(workspace.path, output_files)
                if validation_errors:
                    raise ValueError(f"Build validation failed: {'; '.join(validation_errors)}")

            # Mark task as completed
            task = task_service.update(TaskUpdate(
                id=task_id,
                status="Completed",
                output_files=output_files,
            ))

            execution_logger.log(workspace.path, "Builder Agent", "TASK_COMPLETED", task_id, f"{len(output_files)} files")

            await event_bus.publish(Event(
                type="BUILD_TASK_COMPLETED",
                source="Builder Agent",
                message=f"Builder completed: {task.title} ({len(output_files)} files)",
                severity="success",
                payload={
                    "task_id": task_id,
                    "workspace_id": workspace_id,
                    "title": task.title,
                    "output_files": output_files,
                },
            ))

            # Update agent to idle
            agent_service.update("builder-agent", current_task="Waiting for next task")

            return {"status": "success", "task_id": task_id, "output_files": output_files}

        except Exception as e:
            # Mark task as failed
            task_service.update(TaskUpdate(
                id=task_id,
                status="Failed",
                security_notes=f"Builder error: {str(e)}",
            ))
            agent_service.update("builder-agent", status="Paused", current_task=f"Error: {str(e)[:80]}")

            execution_logger.log(workspace.path, "Builder Agent", "TASK_FAILED", task_id, str(e))

            await event_bus.publish(Event(
                type="BUILD_TASK_FAILED",
                source="Builder Agent",
                message=f"Builder failed on: {task.title} — {str(e)[:120]}",
                severity="error",
                payload={"task_id": task_id, "workspace_id": workspace_id, "error": str(e)},
            ))

            return {"status": "error", "task_id": task_id, "error": str(e)}

    # ── Specialized Handlers ──────────────────────────────────────────────

    async def _create_project_folder(self, workspace) -> list[str]:
        """Task 1: Create the project root folder on disk."""
        project_path = workspace.path.replace("/", os.sep)

        # Sprint 4.5: Validate path before creation
        validate_write_path(workspace.path)

        os.makedirs(project_path, exist_ok=True)

        await event_bus.publish(Event(
            type="FILE_CREATED",
            source="Builder Agent",
            message=f"Created project folder: {workspace.path}",
            severity="success",
            payload={"path": workspace.path},
        ))

        return [workspace.path]

    async def _create_base_structure(self, workspace) -> list[str]:
        """Task 2: Create frontend/, backend/, docs/, .agentos/ directories."""
        base = workspace.path.replace("/", os.sep)

        # Sprint 4.5: Validate base path
        validate_write_path(workspace.path)

        folders = [
            "frontend",
            "frontend/src",
            "frontend/public",
            "backend",
            "backend/app",
            "backend/app/routes",
            "backend/app/models",
            "docs",
            ".agentos",
            ".agentos/logs",
        ]
        created = []

        for folder in folders:
            folder_path = os.path.join(base, folder.replace("/", os.sep))
            os.makedirs(folder_path, exist_ok=True)
            created.append(f"{workspace.path}/{folder}")

            await event_bus.publish(Event(
                type="FILE_CREATED",
                source="Builder Agent",
                message=f"Created directory: {folder}/",
                severity="info",
                payload={"path": f"{workspace.path}/{folder}"},
            ))

        return created

    async def _create_readme(self, workspace, architecture: dict | None = None) -> list[str]:
        """Task 3: Generate README.md with project info."""
        from app.services.task_service import task_service

        if not architecture:
            architecture = self._get_architecture_from_workspace(workspace)
        task_count = task_service.count_total(workspace.id)

        tech_stack = architecture.get("tech_stack", []) if architecture else []
        description = architecture.get("architecture", workspace.description) if architecture else workspace.description
        components = architecture.get("major_components", []) if architecture else []

        content = f"""# {workspace.name}

## Description

{description}

## Tech Stack

{chr(10).join(f'- {t}' for t in tech_stack) if tech_stack else '- To be determined'}

## Major Components

{chr(10).join(f'- {c}' for c in components) if components else '- To be determined'}

## Project Info

| Field | Value |
|-------|-------|
| Generated | {now_label()} |
| Tasks | {task_count} |
| Status | Building |

## Getting Started

Check the `.agentos/project.json` manifest for full project metadata.
"""
        readme_path = os.path.join(workspace.path.replace("/", os.sep), "README.md")
        os.makedirs(os.path.dirname(readme_path), exist_ok=True)
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(content)

        await event_bus.publish(Event(
            type="FILE_CREATED",
            source="Builder Agent",
            message="Created README.md",
            severity="success",
            payload={"path": f"{workspace.path}/README.md"},
        ))

        return [f"{workspace.path}/README.md"]

    async def _create_manifest(self, workspace, architecture: dict | None = None) -> list[str]:
        """Task 4: Generate .agentos/project.json manifest."""
        from app.services.task_service import task_service

        if not architecture:
            architecture = self._get_architecture_from_workspace(workspace)
        tasks = task_service.list_by_workspace(workspace.id)

        manifest = {
            "workspace_id": workspace.id,
            "project_name": workspace.name,
            "path": workspace.path,
            "created_at": workspace.created_at,
            "architecture": architecture,
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status,
                    "priority": t.priority,
                    "assigned_agent": t.assigned_agent,
                }
                for t in tasks
            ],
            "status": "Building",
            "agent_os_version": "0.6.0",
        }

        manifest_path = os.path.join(workspace.path.replace("/", os.sep), ".agentos", "project.json")
        os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, default=str)

        await event_bus.publish(Event(
            type="FILE_CREATED",
            source="Builder Agent",
            message="Created .agentos/project.json",
            severity="success",
            payload={"path": f"{workspace.path}/.agentos/project.json"},
        ))

        return [f"{workspace.path}/.agentos/project.json"]

    # ── Generic LLM-Driven Task Execution ─────────────────────────────────

    async def _generate_for_task(self, task, workspace, architecture: dict | None = None) -> list[str]:
        """Use LLM to generate files for a coding task, with template fallback."""
        from app.services.spec_engine import spec_engine

        if not architecture:
            architecture = self._get_architecture_from_workspace(workspace)
        arch_summary = json.dumps(architecture, default=str) if architecture else "No architecture available"

        # Sprint 4: Load spec for rich project context
        spec = spec_engine.read_spec(workspace.path)
        spec_context = ""
        if spec:
            theme_ctx = spec.get("theme_context", {})
            spec_context = f"""
── PROJECT SPECIFICATION (source of truth) ──────────────────────
Project Name: {spec.get('project_name', workspace.name)}
Theme: {spec.get('theme', 'General')}
Purpose: {spec.get('purpose', 'General')}
Target Users: {spec.get('target_users', 'General Visitors')}
Frontend: {spec.get('frontend', 'React + Vite')}
Backend: {spec.get('backend', False)}
Required Features: {', '.join(spec.get('required_features', []))}
Color Palette: {theme_ctx.get('color_palette', 'N/A')}
Tone: {theme_ctx.get('tone', 'N/A')}
Content Domain: {theme_ctx.get('content_domain', 'N/A')}
Suggested Sections: {', '.join(theme_ctx.get('suggested_sections', []))}
Style Keywords: {', '.join(theme_ctx.get('style_keywords', []))}
─────────────────────────────────────────────────────────────────"""

        prompt = f"""You are a senior frontend developer building a real product. Generate the code files needed for this task.

PROJECT: {workspace.name}
PROJECT PATH: {workspace.path}
{spec_context}
ARCHITECTURE: {arch_summary}

TASK: {task.title}
DESCRIPTION: {task.description}

EXISTING STRUCTURE:
{self._describe_existing_structure(workspace.path)}

Return ONLY valid JSON with this structure:
{{
  "files": [
    {{
      "path": "relative/path/to/file.ext",
      "content": "file content here"
    }}
  ]
}}

STRICT QUALITY STANDARDS:
1. Feature Completion > File Creation: Generate FULLY functioning features, not just placeholder files. Break large tasks into multiple interconnected files (e.g., Components, CSS, Services) and return them all.
2. React/Web Standards: For frontend tasks, implement responsive layouts, modern styling, loading/error states, and proper UI elements (Hero, Nav, Footer, Sections). Include 5+ components and 2+ pages if applicable.
3. Theme-Aware Generation: Use the color palette, tone, and content domain from the spec. Every component must reflect the project's theme visually and in content.
4. Meaningful Content: Do NOT use "Lorem Ipsum", "Hero 1", or generic placeholder text. Write realistic copy that matches the project theme and content domain.
5. Asset Handling: NEVER reference external or non-existent images. Use inline SVG components or CSS-based visuals instead.
6. No Branding: Do NOT include any references to "Agent OS", "scaffolded by", or "generated by" in user-facing code.

Rules:
- Use paths relative to the project root
- Frontend files go under frontend/ (e.g. frontend/src/App.jsx)
- Backend files go under backend/ (e.g. backend/main.py)
- Generate complete, working code
- Do NOT wrap JSON in markdown code fences"""

        try:
            raw = generate_response(BUILDER_MODEL, prompt)
            # Strip think tags
            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            parsed = json.loads(self._extract_json(raw))
            files = parsed.get("files", [])
            if not files:
                raise ValueError("LLM returned empty files list")
        except Exception:
            # Fallback: use project templates instead of creating documentation
            files = self._template_fallback(task, workspace)

        created = []
        for file_info in files:
            rel_path = file_info.get("path", "")
            content = file_info.get("content", "")
            if not rel_path:
                continue

            abs_path = os.path.join(workspace.path.replace("/", os.sep), rel_path.replace("/", os.sep))

            # Sprint 4.5: Validate every file write
            try:
                validate_write_path(abs_path, workspace.path)
            except SecurityViolationError as e:
                logger.warning("Path security blocked file write: %s - %s", rel_path, e)
                continue  # Skip this file, don't abort the whole task

            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)

            normalized = f"{workspace.path}/{rel_path.replace(os.sep, '/')}"
            created.append(normalized)

            await event_bus.publish(Event(
                type="FILE_CREATED",
                source="Builder Agent",
                message=f"Created: {rel_path}",
                severity="info",
                payload={"path": normalized},
            ))

        return created

    # ── Template Fallback ─────────────────────────────────────────────────

    def _template_fallback(self, task, workspace) -> list[dict]:
        """Generate template-based files when LLM is unavailable."""
        task_type = self._detect_task_type(task.title)
        name = workspace.name

        if task_type == "frontend":
            template = FRONTEND_TEMPLATE
        elif task_type == "backend":
            template = BACKEND_TEMPLATE
        elif task_type == "feature":
            template = FEATURE_TEMPLATE
        else:
            # Mixed: create both frontend and backend
            template = {**FRONTEND_TEMPLATE, **BACKEND_TEMPLATE}

        files = []
        for rel_path, content_fn in template.items():
            try:
                content = content_fn(name=name)
            except TypeError:
                content = content_fn()

            # Skip files that already exist on disk
            abs_path = os.path.join(workspace.path.replace("/", os.sep), rel_path.replace("/", os.sep))
            if os.path.exists(abs_path):
                continue

            files.append({"path": rel_path, "content": content})

        return files

    def _detect_task_type(self, title: str) -> str:
        """Categorize a task into frontend, backend, feature, or generic."""
        title_lower = title.lower()
        frontend_score = sum(1 for kw in _FRONTEND_KEYWORDS if kw in title_lower)
        backend_score = sum(1 for kw in _BACKEND_KEYWORDS if kw in title_lower)
        feature_score = sum(1 for kw in _FEATURE_KEYWORDS if kw in title_lower)

        if frontend_score > backend_score and frontend_score > feature_score:
            return "frontend"
        if backend_score > frontend_score and backend_score > feature_score:
            return "backend"
        if feature_score > 0:
            return "feature"
        return "generic"

    # ── Sprint 3: Validation ──────────────────────────────────────────────
    
    def _validate_build_output(self, workspace_path: str, output_files: list[str]) -> list[str]:
        """Validate files exist, are not empty, and imports resolve."""
        errors = []
        for file_path in output_files:
            native_path = file_path.replace("/", os.sep)
            if not os.path.exists(native_path):
                errors.append(f"File missing: {os.path.basename(file_path)}")
                continue
            if os.path.isdir(native_path):
                continue
            if os.path.getsize(native_path) == 0:
                errors.append(f"Empty file: {os.path.basename(file_path)}")

        # Basic structure checks
        pkg_json = os.path.join(workspace_path.replace("/", os.sep), "frontend", "package.json")
        if os.path.exists(pkg_json):
            src_dir = os.path.join(workspace_path.replace("/", os.sep), "frontend", "src")
            if not os.path.exists(src_dir):
                errors.append("frontend/src directory is required but missing")

        # Basic import resolution
        for file_path in output_files:
            native_path = file_path.replace("/", os.sep)
            if not os.path.exists(native_path) or os.path.isdir(native_path):
                continue
            try:
                with open(native_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Check relative imports in JS/JSX
                import_matches = re.findall(r'import\s+.*?from\s+[\'"](\.[^\'"]+)[\'"]', content)
                for imp in import_matches:
                    dir_path = os.path.dirname(native_path)
                    target = os.path.normpath(os.path.join(dir_path, imp))
                    found = False
                    for ext in ["", ".js", ".jsx", ".ts", ".tsx", ".css"]:
                        if os.path.exists(target + ext):
                            found = True
                            break
                    # Also check for index.js inside a folder
                    if not found and os.path.isdir(target):
                        for ext in [".js", ".jsx", ".ts", ".tsx"]:
                            if os.path.exists(os.path.join(target, f"index{ext}")):
                                found = True
                                break
                                
                    if not found:
                         errors.append(f"Broken import '{imp}' in {os.path.basename(file_path)}")
            except Exception:
                pass
                
        return errors

    # ── Helpers ───────────────────────────────────────────────────────────

    def _get_architecture_from_workspace(self, workspace) -> dict | None:
        """Retrieve architecture from the project state manager if available."""
        from app.state.project_state import project_state_manager
        for state in project_state_manager._store.values():
            if state.get("architecture"):
                project_name = state.get("project_name", "")
                # Match by workspace name (case-insensitive)
                if project_name and project_name.lower() == workspace.name.lower():
                    return state["architecture"]
                # Fallback: match by slug
                if project_name and project_name.lower().replace(" ", "-") in workspace.id.lower():
                    return state["architecture"]
        # Last resort: return the first architecture found
        for state in project_state_manager._store.values():
            if state.get("architecture"):
                return state["architecture"]
        return None

    def _extract_json(self, raw: str) -> str:
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "")
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("No JSON found")
        return cleaned[start:end + 1]

    def _describe_existing_structure(self, workspace_path: str) -> str:
        """List the top 2 levels of directories that exist in the workspace."""
        native_path = workspace_path.replace("/", os.sep)
        if not os.path.exists(native_path):
            return "Project directory does not exist yet."

        lines = []
        try:
            for item in sorted(os.listdir(native_path)):
                if item.startswith(".") and item != ".agentos":
                    continue
                item_path = os.path.join(native_path, item)
                if os.path.isdir(item_path):
                    lines.append(f"  {item}/")
                    try:
                        for sub in sorted(os.listdir(item_path))[:10]:
                            sub_path = os.path.join(item_path, sub)
                            suffix = "/" if os.path.isdir(sub_path) else ""
                            lines.append(f"    {sub}{suffix}")
                    except OSError:
                        pass
                else:
                    lines.append(f"  {item}")
        except OSError:
            return "Cannot read project directory."

        return "\n".join(lines) if lines else "Empty project directory."


# ── Singleton ─────────────────────────────────────────────────────────────

builder_service = BuilderService()
