"""
Builder Intelligence Engine — v1.0

Transforms the Builder from a generic LLM wrapper into an intelligent execution engine.
Provides Context Retrieval to limit prompt token explosion and structured Prompt Assembly.
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger("builder_intelligence")

class BuilderIntelligenceEngine:
    """Provides structured context and prompts for the Builder."""
    
    def retrieve_context(self, task: Any, workspace_path: str) -> str:
        """
        Retrieve minimal required context for a task.
        Uses engineering_metadata to pull specific files instead of loading the whole project.
        """
        native_path = workspace_path.replace("/", os.sep)
        context_blocks = []
        
        # 1. Fallback to existing structure if no metadata
        metadata = getattr(task, "engineering_metadata", {}) or {}
        expected_files = metadata.get("expected_files", {})
        
        if not expected_files:
            return f"EXISTING STRUCTURE:\n{self._describe_existing_structure(workspace_path)}"
            
        # 2. Gather specific files requested for reading or modifying
        files_to_read = set(expected_files.get("read", []) + expected_files.get("modify", []))
        
        if not files_to_read:
            return f"EXISTING STRUCTURE:\n{self._describe_existing_structure(workspace_path)}"
            
        context_blocks.append("RELEVANT EXISTING FILES:")
        files_found = 0
        
        for file_rel_path in sorted(files_to_read):
            abs_path = os.path.join(native_path, file_rel_path.replace("/", os.sep))
            if os.path.exists(abs_path) and not os.path.isdir(abs_path):
                try:
                    with open(abs_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    context_blocks.append(f"--- {file_rel_path} ---\n{content}\n")
                    files_found += 1
                except Exception as e:
                    logger.warning(f"Could not read context file {file_rel_path}: {e}")
                    
        # 3. Inject dependency output files (from completed micro-tasks)
        dep_uids = getattr(task, "context_dependencies", []) or []
        if dep_uids:
            from app.services.task_service import task_service
            deps_added = False
            for uid in dep_uids:
                dep_task = task_service.get_by_uid(uid)
                if dep_task and getattr(dep_task, "output_files", None):
                    for fpath in dep_task.output_files[:3]:  # cap at 3 files
                        abs_fpath = os.path.join(native_path, fpath.replace("/", os.sep))
                        if os.path.exists(abs_fpath) and not os.path.isdir(abs_fpath):
                            try:
                                with open(abs_fpath, "r", encoding="utf-8") as f:
                                    content = f.read(8192)  # Cap read size
                                if content:
                                    if not deps_added:
                                        context_blocks.append("\nCONTEXT FROM PREVIOUS TASKS:")
                                        deps_added = True
                                    context_blocks.append(f"--- {fpath} ---\n{content}\n")
                            except Exception as e:
                                logger.warning(f"Could not read dependency file {fpath}: {e}")
        
        if files_found == 0 and not dep_uids:
            return f"EXISTING STRUCTURE:\n{self._describe_existing_structure(workspace_path)}"
            
        return "\n".join(context_blocks)
        
    def assemble_prompt(
        self, 
        task: Any, 
        workspace: Any, 
        architecture: dict | None, 
        spec: dict | None, 
        retrieved_context: str
    ) -> str:
        """Assemble a production-quality prompt with design philosophy, visual standards, and full theme context."""
        arch_summary = json.dumps(architecture, default=str) if architecture else "No architecture available"
        
        # Extract Spec Information
        spec = spec or {}
        theme_ctx = spec.get("theme_context", {})
        
        # ── Full theme context injection (style_keywords + suggested_sections) ──
        style_keywords = theme_ctx.get("style_keywords", [])
        suggested_sections = theme_ctx.get("suggested_sections", [])
        content_domain = theme_ctx.get("content_domain", "")
        animations_hint = theme_ctx.get("animations", [])
        typography_hint = theme_ctx.get("typography", "")
        
        style_kw_str = ", ".join(style_keywords) if style_keywords else "modern, clean, premium"
        sections_str = ", ".join(suggested_sections) if suggested_sections else "N/A"
        animations_str = ", ".join(animations_hint) if animations_hint else "scroll-reveal, hover-scale, fade-in"
        
        spec_context = f"""
── PROJECT SPECIFICATION ───────────────────────────────────────
Project Name: {spec.get('project_name', workspace.name)}
Theme: {spec.get('theme', 'General')}
Purpose: {spec.get('purpose', 'General')}
Target Users: {spec.get('target_users', 'General Visitors')}
Frontend: {spec.get('frontend', 'React + Vite')}
Color Palette: {theme_ctx.get('color_palette', 'N/A')}
Tone: {theme_ctx.get('tone', 'N/A')}
Content Domain: {content_domain or 'N/A'}
Style Keywords: {style_kw_str}
Suggested Sections: {sections_str}
Typography: {typography_hint or 'Inter for body, system-ui fallback'}
Animations: {animations_str}
─────────────────────────────────────────────────────────────────"""

        # Extract Engineering Metadata
        metadata = getattr(task, "engineering_metadata", {}) or {}
        standards = metadata.get("engineering_standards", [])
        deliverables = metadata.get("required_deliverables", [])
        
        standards_section = ""
        if standards:
            standards_list = chr(10).join(f"- {s}" for s in standards)
            standards_section = f"ENGINEERING STANDARDS:\n{standards_list}\n"
            
        deliverables_section = ""
        if deliverables:
            deliv_list = chr(10).join(f"- {d}" for d in deliverables)
            deliverables_section = f"REQUIRED DELIVERABLES:\n{deliv_list}\n"
            
        acceptance_criteria = getattr(task, "acceptance_criteria", [])
        ac_section = ""
        if acceptance_criteria:
            ac_list = chr(10).join(f"- {ac}" for ac in acceptance_criteria)
            ac_section = f"ACCEPTANCE CRITERIA:\n{ac_list}\n"

        prompt = f"""You are a Senior Software Engineer AND Senior Product Designer building a production-quality project.

You are NOT generating minimum-viable code.
You are generating what an experienced design agency would ship for a paying client.

PROJECT: {workspace.name}
{spec_context}
ARCHITECTURE: {arch_summary}

TASK: {task.title}
DESCRIPTION: {task.description}

{ac_section}
{standards_section}
{deliverables_section}
{retrieved_context}

── PRODUCT DESIGN PHILOSOPHY ─────────────────────────────────────
Every component you build must feel intentionally designed and premium.

VISUAL QUALITY:
- Use the Color Palette above as your primary design system.
- Create smooth gradients, layered shadows, and depth using the palette colors.
- Cards must have: rounded corners (12-16px), subtle box-shadows, hover lift effects, and consistent padding.
- Use visual hierarchy: large bold headings, medium subtext, smaller body text.
- Use consistent spacing scale: 8px, 16px, 24px, 32px, 48px, 64px, 96px.
- Never leave large empty whitespace without purpose.
- Use CSS custom properties (--color-primary, --color-accent, etc.) for all theme values.

TYPOGRAPHY:
- Import and use Google Fonts appropriate to the theme (e.g., Inter, Poppins, Playfair Display).
- Headings: bold, large (2rem-3.5rem), with gradient or accent color treatments where appropriate.
- Body: readable (1rem-1.125rem), good line-height (1.6-1.8), proper letter-spacing.
- Use font-weight variations (400, 500, 600, 700) for visual hierarchy.

ANIMATIONS & MICRO-INTERACTIONS:
- Add CSS @keyframes for: fadeIn, slideUp, slideIn, scaleIn.
- Apply entrance animations to sections using animation-delay for staggered reveals.
- All buttons must have hover transitions: transform scale(1.05), background color shift, subtle shadow increase.
- Cards should lift on hover: translateY(-4px) with shadow enhancement.
- Navigation links should have underline or color transitions on hover.
- Use transition: all 0.3s ease for smooth state changes.
- Add a subtle loading/entrance animation when the page first renders.

RESPONSIVE DESIGN:
- Design mobile-first. Base styles target mobile (< 768px).
- Add @media (min-width: 768px) for tablet adjustments.
- Add @media (min-width: 1024px) for desktop layouts.
- Navigation must collapse to a hamburger menu on mobile.
- Grid layouts should stack vertically on mobile, 2-col on tablet, 3-4 col on desktop.
- Font sizes should scale down appropriately on mobile.
- Touch targets must be at least 44px on mobile.

CONTENT QUALITY:
- NEVER use "Lorem ipsum" or placeholder text.
- Generate realistic, domain-appropriate content that matches the theme and content domain.
- Use realistic names, descriptions, prices, testimonials, and data.
- If the project is a coffee shop, write about real-sounding coffee drinks, ambiance, and baristas.
- If the project is a SaaS platform, write about real-sounding features, pricing tiers, and user benefits.
- Include enough content to make every section feel complete and lived-in.

COMPONENT COMPLETENESS:
- Every section should have a heading, descriptive text, and visual elements.
- Hero sections need: headline, subheadline, CTA button(s), and a visual element (gradient, pattern, or icon).
- Feature sections need: 3-6 feature cards with icons (use Unicode/emoji or SVG), titles, and descriptions.
- Testimonial sections need: 3+ testimonials with names, roles, companies, and realistic quotes.
- Footer needs: navigation links, social media links, copyright, and optional newsletter signup.
- Contact sections need: a styled form with proper validation states.

ACCESSIBILITY:
- All interactive elements must have ARIA labels.
- Color contrast must meet WCAG AA (4.5:1 ratio minimum).
- Focus states must be visible on all interactive elements.
- Use semantic HTML throughout (nav, main, section, article, footer, header).
───────────────────────────────────────────────────────────────────

Return ONLY valid JSON with this structure:
{{
  "files": [
    {{
      "path": "relative/path/to/file.ext",
      "content": "file content here (provide FULL updated content if modifying)"
    }}
  ]
}}

STRICT RULES:
1. ONLY generate the requested deliverables. Do not invent unrelated files.
2. If modifying an existing file, output the ENTIRE new content of the file. Do not output partial diffs.
3. Apply the Engineering Standards precisely.
4. Asset Handling: NEVER reference external or non-existent images. Use CSS gradients, SVG inline, or Unicode emoji instead.
5. Do NOT wrap JSON in markdown code fences.
6. Return syntactically valid JSON.
"""
        return prompt
        
    def _describe_existing_structure(self, workspace_path: str) -> str:
        """Fallback context retrieval."""
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

# Singleton
builder_intelligence = BuilderIntelligenceEngine()
