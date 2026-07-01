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
from app.services.builder_intelligence import builder_intelligence

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
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
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

    "frontend/src/App.jsx": lambda name, **kw: f"""import React, {{ useState }} from 'react'

const features = [
  {{ icon: '\\u2728', title: 'Modern Design', desc: 'Crafted with attention to every pixel, delivering a premium visual experience.' }},
  {{ icon: '\\u26A1', title: 'Lightning Fast', desc: 'Optimized performance with instant load times and smooth interactions.' }},
  {{ icon: '\\U0001F6E1\\uFE0F', title: 'Secure & Reliable', desc: 'Built with industry-standard security practices to protect your data.' }},
  {{ icon: '\\U0001F4F1', title: 'Fully Responsive', desc: 'Perfect experience across desktop, tablet, and mobile devices.' }},
  {{ icon: '\\U0001F3A8', title: 'Customizable', desc: 'Easily adaptable to match your brand identity and preferences.' }},
  {{ icon: '\\U0001F680', title: 'Scalable', desc: 'Architecture designed to grow seamlessly with your business needs.' }},
]

const testimonials = [
  {{ name: 'Sarah Chen', role: 'Product Manager', quote: 'This platform transformed how our team collaborates. The intuitive design made onboarding effortless.' }},
  {{ name: 'Marcus Williams', role: 'CTO, TechFlow', quote: 'Exceptional quality and attention to detail. It feels like it was custom-built for our needs.' }},
  {{ name: 'Elena Rodriguez', role: 'Design Lead', quote: 'The best tool we have adopted this year. Clean, fast, and beautifully designed.' }},
]

export default function App() {{
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="app">
      {{/* Navigation */}}
      <nav className="navbar">
        <div className="nav-container">
          <a href="#" className="nav-logo">{name}</a>
          <button className="nav-toggle" onClick={{() => setMenuOpen(!menuOpen)}} aria-label="Toggle menu">
            {{menuOpen ? '\\u2715' : '\\u2630'}}
          </button>
          <ul className={{`nav-links ${{menuOpen ? 'active' : ''}}`}}>
            <li><a href="#features" onClick={{() => setMenuOpen(false)}}>Features</a></li>
            <li><a href="#testimonials" onClick={{() => setMenuOpen(false)}}>Testimonials</a></li>
            <li><a href="#contact" onClick={{() => setMenuOpen(false)}}>Contact</a></li>
            <li><a href="#contact" className="nav-cta" onClick={{() => setMenuOpen(false)}}>Get Started</a></li>
          </ul>
        </div>
      </nav>

      {{/* Hero */}}
      <section className="hero">
        <div className="hero-content">
          <h1 className="hero-title">Welcome to <span className="gradient-text">{name}</span></h1>
          <p className="hero-subtitle">Discover a premium experience crafted with modern design, powerful features, and seamless performance.</p>
          <div className="hero-actions">
            <a href="#features" className="btn btn-primary">Explore Features</a>
            <a href="#contact" className="btn btn-outline">Get in Touch</a>
          </div>
        </div>
        <div className="hero-glow"></div>
      </section>

      {{/* Features */}}
      <section id="features" className="section features-section">
        <div className="container">
          <h2 className="section-title">Why Choose Us</h2>
          <p className="section-subtitle">Everything you need, nothing you don't.</p>
          <div className="features-grid">
            {{features.map((f, i) => (
              <div key={{i}} className="feature-card" style={{{{ animationDelay: `${{i * 0.1}}s` }}}}>
                <span className="feature-icon">{{f.icon}}</span>
                <h3>{{f.title}}</h3>
                <p>{{f.desc}}</p>
              </div>
            ))}}
          </div>
        </div>
      </section>

      {{/* Testimonials */}}
      <section id="testimonials" className="section testimonials-section">
        <div className="container">
          <h2 className="section-title">What People Say</h2>
          <p className="section-subtitle">Trusted by teams around the world.</p>
          <div className="testimonials-grid">
            {{testimonials.map((t, i) => (
              <div key={{i}} className="testimonial-card" style={{{{ animationDelay: `${{i * 0.15}}s` }}}}>
                <p className="testimonial-quote">"{{t.quote}}"</p>
                <div className="testimonial-author">
                  <div className="testimonial-avatar">{{t.name[0]}}</div>
                  <div><strong>{{t.name}}</strong><span>{{t.role}}</span></div>
                </div>
              </div>
            ))}}
          </div>
        </div>
      </section>

      {{/* CTA */}}
      <section className="section cta-section">
        <div className="container">
          <h2>Ready to Get Started?</h2>
          <p>Join thousands of satisfied users and take your experience to the next level.</p>
          <a href="#contact" className="btn btn-primary btn-lg">Start Now</a>
        </div>
      </section>

      {{/* Contact */}}
      <section id="contact" className="section contact-section">
        <div className="container">
          <h2 className="section-title">Get in Touch</h2>
          <p className="section-subtitle">We would love to hear from you.</p>
          <form className="contact-form" onSubmit={{(e) => e.preventDefault()}}>
            <input type="text" placeholder="Your Name" required />
            <input type="email" placeholder="Your Email" required />
            <textarea placeholder="Your Message" rows="5" required></textarea>
            <button type="submit" className="btn btn-primary">Send Message</button>
          </form>
        </div>
      </section>

      {{/* Footer */}}
      <footer className="footer">
        <div className="footer-container">
          <div className="footer-brand"><h3>{name}</h3><p>Crafted with care. Built for excellence.</p></div>
          <div className="footer-links"><h4>Quick Links</h4><a href="#features">Features</a><a href="#testimonials">Testimonials</a><a href="#contact">Contact</a></div>
          <div className="footer-links"><h4>Legal</h4><a href="#">Privacy Policy</a><a href="#">Terms of Service</a></div>
        </div>
        <div className="footer-bottom"><p>&copy; {{new Date().getFullYear()}} {name}. All rights reserved.</p></div>
      </footer>
    </div>
  )
}}
""",

    "frontend/src/index.css": lambda name, **kw: """@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  --color-primary: #3b82f6;
  --color-primary-dark: #2563eb;
  --color-accent: #06b6d4;
  --color-bg: #0f172a;
  --color-bg-alt: #1e293b;
  --color-surface: rgba(30, 41, 59, 0.6);
  --color-text: #e2e8f0;
  --color-text-muted: #94a3b8;
  --color-border: rgba(148, 163, 184, 0.1);
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --shadow-sm: 0 2px 8px rgba(0,0,0,0.15);
  --shadow-md: 0 4px 16px rgba(0,0,0,0.2);
  --shadow-lg: 0 8px 32px rgba(0,0,0,0.3);
  --transition: all 0.3s ease;
}

*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  font-family: 'Inter', system-ui, sans-serif;
  background: var(--color-bg);
  color: var(--color-text);
  min-height: 100vh;
  line-height: 1.7;
}

@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes slideUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
@keyframes scaleIn { from { opacity: 0; transform: scale(0.9); } to { opacity: 1; transform: scale(1); } }

.container { max-width: 1120px; margin: 0 auto; padding: 0 24px; }
.section { padding: 96px 0; }
.section-title {
  font-size: 2.25rem; font-weight: 800; text-align: center; margin-bottom: 12px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.section-subtitle { text-align: center; color: var(--color-text-muted); margin-bottom: 48px; font-size: 1.125rem; }

.btn {
  display: inline-block; padding: 14px 32px; border-radius: var(--radius-sm); font-weight: 600;
  font-size: 1rem; text-decoration: none; transition: var(--transition); cursor: pointer; border: none;
}
.btn-primary { background: var(--color-primary); color: #fff; }
.btn-primary:hover { background: var(--color-primary-dark); transform: translateY(-2px); box-shadow: var(--shadow-md); }
.btn-outline { border: 2px solid var(--color-primary); color: var(--color-primary); background: transparent; }
.btn-outline:hover { background: var(--color-primary); color: #fff; transform: translateY(-2px); }
.btn-lg { padding: 16px 40px; font-size: 1.125rem; }

.navbar {
  position: sticky; top: 0; z-index: 100;
  background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--color-border);
}
.nav-container { max-width: 1120px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; }
.nav-logo { font-size: 1.5rem; font-weight: 800; color: var(--color-text); text-decoration: none; }
.nav-toggle { display: none; background: none; border: none; color: var(--color-text); font-size: 1.5rem; cursor: pointer; }
.nav-links { display: flex; list-style: none; gap: 32px; align-items: center; }
.nav-links a { color: var(--color-text-muted); text-decoration: none; font-weight: 500; transition: var(--transition); }
.nav-links a:hover { color: var(--color-primary); }
.nav-cta { background: var(--color-primary) !important; color: #fff !important; padding: 10px 24px !important; border-radius: var(--radius-sm) !important; }

.hero {
  position: relative; min-height: 90vh; display: flex; align-items: center; justify-content: center;
  text-align: center; padding: 120px 24px 96px; overflow: hidden;
}
.hero-content { position: relative; z-index: 1; animation: slideUp 0.8s ease; }
.hero-title { font-size: 3.5rem; font-weight: 800; line-height: 1.15; margin-bottom: 20px; }
.gradient-text {
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.hero-subtitle { font-size: 1.25rem; color: var(--color-text-muted); max-width: 600px; margin: 0 auto 32px; line-height: 1.7; }
.hero-actions { display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; }
.hero-glow {
  position: absolute; width: 500px; height: 500px; border-radius: 50%;
  background: radial-gradient(circle, rgba(59,130,246,0.15), transparent 70%);
  top: 50%; left: 50%; transform: translate(-50%,-50%); pointer-events: none;
}

.features-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.feature-card {
  background: var(--color-surface); border: 1px solid var(--color-border);
  border-radius: var(--radius-lg); padding: 32px; transition: var(--transition);
  animation: slideUp 0.6s ease both;
}
.feature-card:hover { transform: translateY(-6px); box-shadow: var(--shadow-lg); border-color: rgba(59,130,246,0.3); }
.feature-icon { font-size: 2.5rem; display: block; margin-bottom: 16px; }
.feature-card h3 { font-size: 1.25rem; font-weight: 700; margin-bottom: 8px; }
.feature-card p { color: var(--color-text-muted); font-size: 0.95rem; line-height: 1.6; }

.testimonials-section { background: var(--color-bg-alt); }
.testimonials-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.testimonial-card {
  background: var(--color-surface); border: 1px solid var(--color-border);
  border-radius: var(--radius-lg); padding: 32px; animation: scaleIn 0.5s ease both;
}
.testimonial-quote { font-size: 1rem; line-height: 1.7; margin-bottom: 20px; font-style: italic; }
.testimonial-author { display: flex; align-items: center; gap: 12px; }
.testimonial-avatar {
  width: 44px; height: 44px; border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  display: flex; align-items: center; justify-content: center; font-weight: 700; color: #fff;
}
.testimonial-author strong { display: block; font-size: 0.95rem; }
.testimonial-author span { color: var(--color-text-muted); font-size: 0.85rem; }

.cta-section {
  text-align: center;
  background: linear-gradient(135deg, rgba(59,130,246,0.1), rgba(6,182,212,0.1));
  border-top: 1px solid var(--color-border); border-bottom: 1px solid var(--color-border);
}
.cta-section h2 { font-size: 2rem; font-weight: 800; margin-bottom: 12px; }
.cta-section p { color: var(--color-text-muted); margin-bottom: 32px; font-size: 1.125rem; }

.contact-form { max-width: 560px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }
.contact-form input, .contact-form textarea {
  background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-sm);
  padding: 14px 18px; color: var(--color-text); font-family: inherit; font-size: 1rem; transition: var(--transition);
}
.contact-form input:focus, .contact-form textarea:focus {
  outline: none; border-color: var(--color-primary); box-shadow: 0 0 0 3px rgba(59,130,246,0.15);
}

.footer { background: var(--color-bg-alt); border-top: 1px solid var(--color-border); padding: 64px 0 0; }
.footer-container { max-width: 1120px; margin: 0 auto; padding: 0 24px; display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 48px; }
.footer-brand h3 { font-size: 1.5rem; font-weight: 800; margin-bottom: 8px; }
.footer-brand p { color: var(--color-text-muted); }
.footer-links h4 { font-weight: 700; margin-bottom: 16px; }
.footer-links a { display: block; color: var(--color-text-muted); text-decoration: none; margin-bottom: 10px; transition: var(--transition); }
.footer-links a:hover { color: var(--color-primary); }
.footer-bottom { text-align: center; padding: 24px; margin-top: 48px; border-top: 1px solid var(--color-border); color: var(--color-text-muted); font-size: 0.875rem; }

@media (max-width: 768px) {
  .nav-toggle { display: block; }
  .nav-links {
    position: fixed; top: 0; right: -100%; width: 75%; height: 100vh;
    background: var(--color-bg-alt); flex-direction: column; padding: 80px 32px 32px;
    transition: right 0.3s ease; z-index: 200;
  }
  .nav-links.active { right: 0; }
  .hero-title { font-size: 2.25rem; }
  .hero { min-height: auto; padding: 100px 24px 64px; }
  .features-grid, .testimonials-grid { grid-template-columns: 1fr; }
  .footer-container { grid-template-columns: 1fr; gap: 32px; }
  .hero-actions { flex-direction: column; align-items: center; }
}
@media (min-width: 769px) and (max-width: 1024px) {
  .features-grid, .testimonials-grid { grid-template-columns: repeat(2, 1fr); }
  .hero-title { font-size: 2.75rem; }
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
        """Use LLM to generate files for a coding task, with Intelligence Engine and retry fallback."""
        from app.services.spec_engine import spec_engine

        if not architecture:
            architecture = self._get_architecture_from_workspace(workspace)

        spec = spec_engine.read_spec(workspace.path)
        
        # ── Builder Intelligence Engine ──
        retrieved_context = builder_intelligence.retrieve_context(task, workspace.path)
        prompt = builder_intelligence.assemble_prompt(task, workspace, architecture, spec, retrieved_context)

        max_retries = 1
        created = []
        files = []

        for attempt in range(max_retries + 1):
            try:
                raw = generate_response(BUILDER_MODEL, prompt)
                # Strip think tags
                raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
                parsed = json.loads(self._extract_json(raw))
                files = parsed.get("files", [])
                
                if not files:
                    raise ValueError("LLM returned empty files list")
                    
                # Write files
                created = []
                for file_info in files:
                    rel_path = file_info.get("path", "")
                    content = file_info.get("content", "")
                    if not rel_path:
                        continue

                    abs_path = os.path.join(workspace.path.replace("/", os.sep), rel_path.replace("/", os.sep))

                    try:
                        validate_write_path(abs_path, workspace.path)
                    except SecurityViolationError as e:
                        logger.warning("Path security blocked file write: %s - %s", rel_path, e)
                        continue

                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                    with open(abs_path, "w", encoding="utf-8") as f:
                        f.write(content)

                    normalized = f"{workspace.path}/{rel_path.replace(os.sep, '/')}"
                    created.append(normalized)

                # ── Sprint 3: Build Validation Layer (Now with retries) ──
                validation_errors = self._validate_build_output(workspace.path, created, task)
                if validation_errors:
                    raise ValueError(f"Build validation failed: {'; '.join(validation_errors)}")

                # Success, break out of retry loop
                for norm_path in created:
                    rel_path = norm_path.replace(f"{workspace.path}/", "")
                    await event_bus.publish(Event(
                        type="FILE_CREATED",
                        source="Builder Agent",
                        message=f"Created: {rel_path}",
                        severity="info",
                        payload={"path": norm_path},
                    ))
                break

            except Exception as e:
                logger.warning(f"Generation attempt {attempt + 1} failed: {e}")
                if attempt == max_retries:
                    logger.error(f"Max retries reached for task {task.title}. Falling back to template.")
                    files = self._template_fallback(task, workspace)
                    created = []
                    for file_info in files:
                        rel_path = file_info.get("path", "")
                        content = file_info.get("content", "")
                        if not rel_path:
                            continue
                        abs_path = os.path.join(workspace.path.replace("/", os.sep), rel_path.replace("/", os.sep))
                        try:
                            validate_write_path(abs_path, workspace.path)
                        except SecurityViolationError:
                            continue
                        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                        with open(abs_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        normalized = f"{workspace.path}/{rel_path.replace(os.sep, '/')}"
                        created.append(normalized)
                        await event_bus.publish(Event(
                            type="FILE_CREATED",
                            source="Builder Agent",
                            message=f"Created (Template): {rel_path}",
                            severity="info",
                            payload={"path": normalized},
                        ))
                    break
                else:
                    # Append error for retry
                    prompt += f"\n\nERROR IN PREVIOUS ATTEMPT:\n{str(e)}\nPlease fix the errors and try again."

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
    
    def _validate_build_output(self, workspace_path: str, output_files: list[str], task=None) -> list[str]:
        """Validate files exist, are not empty, imports resolve, and deliverables are met."""
        errors = []
        
        # 1. Check for expected deliverables if task is provided
        if task:
            metadata = getattr(task, "engineering_metadata", {}) or {}
            deliverables = metadata.get("required_deliverables", [])
            
            # Simple check: do the output files somehow mention the deliverables?
            # Or are they present in the workspace? We check if the files created cover them.
            output_basenames = [os.path.basename(f) for f in output_files]
            
            # A rigorous check would parse the codebase, but a simple basename/path heuristic works for the agent.
            for d in deliverables:
                # E.g. "Navbar.jsx" -> check if any output file contains "Navbar"
                clean_d = d.replace(".jsx", "").replace(".js", "").replace(".py", "")
                found = any(clean_d.lower() in f.lower() for f in output_files)
                if not found:
                    errors.append(f"Missing required deliverable: {d}")

        # 2. Check for empty files
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

# ── Singleton ─────────────────────────────────────────────────────────────

builder_service = BuilderService()
