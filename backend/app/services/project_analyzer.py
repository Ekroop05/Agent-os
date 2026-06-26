"""Sprint 5: Project Analysis Engine (Feature 2)

Analyzes an existing project directory to understand its structure,
framework, components, pages, routes, dependencies, and configuration.
This is a READ-ONLY service — it never modifies project files.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("project_analyzer")

# Framework detection rules: config_file -> framework_name
FRAMEWORK_SIGNATURES = {
    "vite.config.js": "Vite",
    "vite.config.ts": "Vite",
    "next.config.js": "Next.js",
    "next.config.mjs": "Next.js",
    "next.config.ts": "Next.js",
    "nuxt.config.js": "Nuxt",
    "nuxt.config.ts": "Nuxt",
    "angular.json": "Angular",
    "svelte.config.js": "SvelteKit",
    "gatsby-config.js": "Gatsby",
    "remix.config.js": "Remix",
    "astro.config.mjs": "Astro",
    "manage.py": "Django",
    "app.py": "Flask",
    "requirements.txt": "Python",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
}

# File extensions to category mapping
EXT_CATEGORIES = {
    ".jsx": "component", ".tsx": "component", ".vue": "component", ".svelte": "component",
    ".js": "script", ".ts": "script", ".mjs": "script",
    ".css": "style", ".scss": "style", ".less": "style", ".sass": "style",
    ".html": "template", ".ejs": "template", ".hbs": "template",
    ".json": "config", ".yaml": "config", ".yml": "config", ".toml": "config",
    ".py": "python", ".rb": "ruby", ".go": "go", ".rs": "rust",
    ".md": "documentation", ".txt": "documentation",
    ".png": "asset", ".jpg": "asset", ".jpeg": "asset", ".svg": "asset",
    ".gif": "asset", ".ico": "asset", ".webp": "asset",
    ".woff": "font", ".woff2": "font", ".ttf": "font", ".eot": "font",
}

# Directories to skip during analysis
SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".next", ".nuxt", "dist", "build",
    ".venv", "venv", "env", ".env", ".cache", "coverage", ".turbo",
    ".svelte-kit", ".output", "target", ".snapshots",
}

MAX_DEPTH = 6
MAX_FILES = 2000


class ProjectAnalyzer:
    """Analyzes project directories to extract structure and metadata."""

    def analyze(self, project_path: str) -> dict:
        """Analyze a project directory and return structured analysis."""
        root = Path(project_path)
        if not root.exists() or not root.is_dir():
            return {"error": f"Path does not exist or is not a directory: {project_path}"}

        logger.info("Analyzing project at: %s", project_path)

        framework = self._detect_framework(root)
        dependencies = self._read_dependencies(root)
        file_tree = self._scan_tree(root, root, depth=0)
        file_counts = self._count_files_by_category(root)

        # Detect components, pages, routes, services, assets
        components = self._find_by_directory(root, ["components", "component", "ui", "shared"])
        pages = self._find_by_directory(root, ["pages", "views", "screens", "app"])
        routes = self._find_routes(root)
        services = self._find_by_directory(root, ["services", "api", "lib", "utils", "helpers"])
        assets = self._find_by_directory(root, ["assets", "public", "static", "images", "media"])
        configs = self._find_configs(root)

        analysis = {
            "project_path": project_path,
            "project_name": root.name,
            "framework": framework,
            "dependencies": dependencies,
            "file_tree": file_tree,
            "file_counts": file_counts,
            "total_files": sum(file_counts.values()),
            "components": components,
            "pages": pages,
            "routes": routes,
            "services": services,
            "assets": assets,
            "configs": configs,
            "component_count": len(components),
            "page_count": len(pages),
            "route_count": len(routes),
            "service_count": len(services),
            "risk_assessment": self._assess_risk(file_counts, framework),
        }

        logger.info(
            "Analysis complete: %s (%s) — %d files, %d components, %d pages",
            root.name, framework, analysis["total_files"],
            analysis["component_count"], analysis["page_count"],
        )
        return analysis

    def _detect_framework(self, root: Path) -> str:
        """Detect the primary framework by checking for signature config files."""
        for config_file, framework in FRAMEWORK_SIGNATURES.items():
            if (root / config_file).exists():
                return framework

        # Check package.json for framework dependencies
        pkg_path = root / "package.json"
        if pkg_path.exists():
            try:
                pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "react" in deps:
                    if "next" in deps:
                        return "Next.js"
                    return "React"
                if "vue" in deps:
                    return "Vue"
                if "svelte" in deps:
                    return "Svelte"
                if "@angular/core" in deps:
                    return "Angular"
                return "Node.js"
            except (json.JSONDecodeError, OSError):
                pass

        if (root / "requirements.txt").exists() or (root / "pyproject.toml").exists():
            return "Python"

        return "Unknown"

    def _read_dependencies(self, root: Path) -> dict:
        """Read dependency information from package.json or requirements.txt."""
        result = {"production": [], "development": []}

        pkg_path = root / "package.json"
        if pkg_path.exists():
            try:
                pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
                result["production"] = list(pkg.get("dependencies", {}).keys())
                result["development"] = list(pkg.get("devDependencies", {}).keys())
            except (json.JSONDecodeError, OSError):
                pass

        req_path = root / "requirements.txt"
        if req_path.exists():
            try:
                lines = req_path.read_text(encoding="utf-8").strip().splitlines()
                result["production"] = [
                    line.split("==")[0].split(">=")[0].strip()
                    for line in lines if line.strip() and not line.startswith("#")
                ]
            except OSError:
                pass

        return result

    def _scan_tree(self, root: Path, current: Path, depth: int) -> list[dict]:
        """Recursively scan directory tree up to MAX_DEPTH."""
        if depth > MAX_DEPTH:
            return []

        entries = []
        try:
            for item in sorted(current.iterdir()):
                if item.name.startswith(".") and item.name not in (".env.example",):
                    continue
                if item.name in SKIP_DIRS:
                    continue

                rel_path = str(item.relative_to(root)).replace("\\", "/")

                if item.is_dir():
                    children = self._scan_tree(root, item, depth + 1)
                    entries.append({
                        "name": item.name,
                        "path": rel_path,
                        "type": "directory",
                        "children": children,
                        "count": sum(1 for c in children if c["type"] == "file") + sum(
                            c.get("count", 0) for c in children if c["type"] == "directory"
                        ),
                    })
                elif item.is_file():
                    ext = item.suffix.lower()
                    entries.append({
                        "name": item.name,
                        "path": rel_path,
                        "type": "file",
                        "extension": ext,
                        "category": EXT_CATEGORIES.get(ext, "other"),
                        "size": item.stat().st_size,
                    })
        except PermissionError:
            pass

        return entries

    def _count_files_by_category(self, root: Path) -> dict:
        """Count files by category."""
        counts = {}
        file_count = 0
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            for filename in filenames:
                file_count += 1
                if file_count > MAX_FILES:
                    return counts
                ext = Path(filename).suffix.lower()
                category = EXT_CATEGORIES.get(ext, "other")
                counts[category] = counts.get(category, 0) + 1
        return counts

    def _find_by_directory(self, root: Path, dir_names: list[str]) -> list[str]:
        """Find files inside specific directory names."""
        results = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            current_dir = Path(dirpath).name.lower()
            if current_dir in dir_names:
                for filename in filenames:
                    rel = str(Path(dirpath, filename).relative_to(root)).replace("\\", "/")
                    results.append(rel)
        return results[:200]  # Cap results

    def _find_routes(self, root: Path) -> list[str]:
        """Detect route files and route definitions."""
        route_files = []
        route_patterns = ["routes", "router", "routing", "app"]
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            for filename in filenames:
                name_lower = filename.lower()
                if any(p in name_lower for p in route_patterns) and Path(filename).suffix in (".js", ".jsx", ".ts", ".tsx", ".py"):
                    rel = str(Path(dirpath, filename).relative_to(root)).replace("\\", "/")
                    route_files.append(rel)
        return route_files[:100]

    def _find_configs(self, root: Path) -> list[str]:
        """Find configuration files in the project root."""
        config_extensions = {".json", ".yaml", ".yml", ".toml", ".env", ".config.js", ".config.ts"}
        configs = []
        try:
            for item in root.iterdir():
                if item.is_file():
                    name = item.name.lower()
                    if item.suffix in config_extensions or "config" in name or name.startswith("."):
                        configs.append(item.name)
        except PermissionError:
            pass
        return configs

    def _assess_risk(self, file_counts: dict, framework: str) -> dict:
        """Generate a modification risk assessment."""
        total = sum(file_counts.values())
        complexity = "Low" if total < 50 else "Medium" if total < 200 else "High"
        return {
            "complexity": complexity,
            "total_files": total,
            "framework_known": framework != "Unknown",
            "recommendation": (
                "Safe to modify with standard precautions."
                if complexity == "Low" else
                "Create a snapshot before modifying. Review change plan carefully."
                if complexity == "Medium" else
                "High-complexity project. Strongly recommend snapshot and incremental changes."
            ),
        }


project_analyzer = ProjectAnalyzer()
