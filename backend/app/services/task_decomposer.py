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
    acceptance_criteria: list[str] | None = None,
    complexity: str = "S",
    estimated_context: list[str] | None = None,
    objective: str | None = None,
    epic: str | None = None,
    feature: str | None = None,
    story: str | None = None,
    task_uid: str | None = None,
    context_dependencies: list[str] | None = None,
    engineering_metadata: dict | None = None,
) -> dict:
    """Create a standardised atomic task dict."""
    return {
        "title": title,
        "description": description,
        "type": task_type,
        "expected_output": expected_output,
        "dependencies": dependencies or [],
        "priority": priority,
        "acceptance_criteria": acceptance_criteria or [f"Verify {title} works correctly."],
        "complexity": complexity,
        "estimated_context": estimated_context or [],
        "objective": objective or f"Objective: {title}",
        "epic": epic,
        "feature": feature,
        "story": story,
        "task_uid": task_uid,
        "context_dependencies": context_dependencies or [],
        "engineering_metadata": engineering_metadata or {},
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
            f"Create a comprehensive design system for the {theme} theme. "
            f"Include: CSS custom properties for all colors from the palette, "
            f"typography scale (h1-h6, body, small), spacing scale (4px to 96px), "
            f"border-radius tokens, shadow tokens (sm, md, lg, xl), "
            f"transition tokens, and responsive breakpoints (768px, 1024px, 1280px). "
            f"Import Google Fonts appropriate to the theme. "
            f"Create index.css with: global reset, smooth scroll, body font settings, "
            f"selection colors, scrollbar styling, and @keyframes for fadeIn, slideUp, slideIn, scaleIn animations. "
            f"This file is the design foundation — every component will reference these variables.",
            "frontend",
            "src/index.css created with CSS custom properties, animations, typography scale, and global styles",
            dependencies=[f"Create {frontend} Project"],
        ),
        _task(
            "Create Navbar Component",
            f"Create a premium responsive navigation bar for {name}. "
            f"Desktop: sticky header with logo, navigation links with hover underline animations, and a CTA button. "
            f"Mobile: hamburger menu icon that animates to X on toggle, slide-in mobile menu with backdrop overlay. "
            f"Use the {theme} theme colors. Include smooth scroll-to-section for anchor links. "
            f"Add a subtle background blur/color change on scroll (glassmorphism effect). "
            f"Navigation links should have smooth color transitions on hover.",
            "frontend",
            "src/components/Navbar.jsx and src/components/Navbar.css created and exported",
            dependencies=["Create Theme Variables and Global Styles"],
        ),
        _task(
            "Create Footer Component",
            f"Create a premium multi-column footer for {name}. "
            f"Include: brand logo and tagline, 3-4 link columns (Quick Links, Services, Company, Legal), "
            f"social media icon links with hover color transitions, "
            f"optional newsletter signup with styled input and button, "
            f"and a bottom bar with copyright and 'Back to top' button. "
            f"Use the {theme} theme colors with a darker background variant. "
            f"Responsive: stack columns vertically on mobile.",
            "frontend",
            "src/components/Footer.jsx and src/components/Footer.css created and exported",
            dependencies=["Create Theme Variables and Global Styles"],
        ),
    ]

    # Add Hero Section if in features
    if any("hero" in f.lower() for f in features):
        tasks.append(_task(
            "Create Hero Section Component",
            f"Create a visually stunning hero section for {name}. "
            f"Include: large gradient headline text, descriptive subheadline, "
            f"two CTA buttons (primary filled, secondary outlined) with hover animations, "
            f"and a decorative visual element (CSS gradient orb, geometric pattern, or abstract shape). "
            f"Add a fadeIn + slideUp entrance animation on load. "
            f"Use the {theme} theme colors and tone. "
            f"The hero should be full viewport height (100vh) on desktop, auto on mobile. "
            f"Content should be centered with proper max-width constraints.",
            "frontend",
            "src/components/Hero.jsx and src/components/Hero.css created and exported",
            dependencies=["Create Theme Variables and Global Styles"],
        ))

    tasks.append(_task(
        "Create Home Page Layout",
        f"Create the main Home page that assembles ALL components into a complete, cohesive page for {name}. "
        f"Import and render: Navbar, Hero, and every feature section component created for this project, then Footer. "
        f"Add section IDs for smooth scroll navigation. "
        f"Ensure proper vertical spacing between sections (64-96px gaps). "
        f"The page should feel like a complete, professional website — not a stack of isolated components.",
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
        f"Review and enhance responsive CSS across ALL components for {name}. "
        f"Ensure: navigation collapses to hamburger on mobile (<768px), "
        f"grid layouts stack vertically on mobile and adapt to 2-col on tablet, "
        f"typography scales down appropriately, "
        f"touch targets are at least 44px on mobile, "
        f"horizontal padding increases on desktop for comfortable reading width, "
        f"and hero section adapts from full-height on desktop to auto-height on mobile. "
        f"Test breakpoints: 375px (mobile), 768px (tablet), 1024px (desktop), 1280px (wide).",
        "frontend",
        "All component CSS files updated with @media queries",
        dependencies=["Create App Shell with Routing"],
        priority="Medium",
    ))

    return tasks


def _decompose_frontend_features(spec: dict) -> list[dict]:
    """Decompose feature implementation into per-feature atomic micro-tasks.

    Each feature maps to a **list** of sequential micro-tasks (typically CSS
    first, then JSX) so the 7B model only writes ONE file per task.
    """
    features = spec.get("required_features", [])
    theme = spec.get("theme", "General")
    name = spec.get("project_name", "Project")
    tasks = []

    # ── Feature → list-of-micro-tasks map ─────────────────────────────────
    # Each entry is a list of dicts.  When ``depends_on_prev`` is True the
    # task is wired to depend on the immediately preceding task in the list;
    # otherwise it depends on "Create Theme Variables and Global Styles".

    _feature_map: dict[str, list[dict]] = {
        "hero section": [
            {
                "title": "Create Hero Section Styling",
                "desc": f"Create the CSS file for the Hero section of {name}. "
                       f"Include: full-viewport hero layout, gradient text effect, dual-button row, "
                       f"radial glow background, fadeIn + slideUp @keyframes, responsive breakpoints. "
                       f"Use {theme} theme colors via CSS custom properties.",
                "output": "src/components/Hero.css created",
            },
            {
                "title": "Create Hero Section Component",
                "desc": f"Create the JSX component for the Hero section of {name}. "
                       f"Import Hero.css. Render: large gradient headline, descriptive subheadline, "
                       f"two CTA buttons (primary + outlined) with hover animations, and a decorative "
                       f"CSS gradient orb. Use {theme} theme colors.",
                "output": "src/components/Hero.jsx created",
                "depends_on_prev": True,
            },
        ],
        "about section": [
            {
                "title": "Create About Section Styling",
                "desc": f"Create the CSS file for the About section of {name}. "
                       f"Include: two-column layout, stat counter styles, slideUp animation, "
                       f"responsive stacking for mobile. Use {theme} theme colors.",
                "output": "src/components/About.css created",
            },
            {
                "title": "Create About Section Component",
                "desc": f"Create the JSX component for the About section of {name}. "
                       f"Import About.css. Render: heading, mission statement, 3 key stats with "
                       f"large numbers and labels, decorative visual element. "
                       f"Use realistic, domain-appropriate content for the {theme} domain.",
                "output": "src/components/About.jsx created",
                "depends_on_prev": True,
            },
        ],
        "contact section": [
            {
                "title": "Create Contact Section Styling",
                "desc": f"Create the CSS file for the Contact section of {name}. "
                       f"Include: two-column layout, form input focus states, submit button animation, "
                       f"icon styling for contact info, responsive stacking. Use {theme} theme colors.",
                "output": "src/components/Contact.css created",
            },
            {
                "title": "Create Contact Section Component",
                "desc": f"Create the JSX component for the Contact section of {name}. "
                       f"Import Contact.css. Render: left column with contact info (email, phone, "
                       f"address with icons), right column with styled form (name, email, subject, "
                       f"message) with validation and animated submit button. Use {theme} theme colors.",
                "output": "src/components/Contact.jsx created",
                "depends_on_prev": True,
            },
        ],
        "contact form": [
            {
                "title": "Create Contact Form Styling",
                "desc": f"Create the CSS file for the ContactForm component of {name}. "
                       f"Include: input focus states, validation styling, button hover effects.",
                "output": "src/components/ContactForm.css created",
            },
            {
                "title": "Create Contact Form Component",
                "desc": f"Create the JSX component for the ContactForm of {name}. "
                       f"Import ContactForm.css. Render: name, email, message fields with validation.",
                "output": "src/components/ContactForm.jsx created",
                "depends_on_prev": True,
            },
        ],
        "navigation": [
            {
                "title": "Create Navigation Styling",
                "desc": f"Create the CSS file for the Navbar of {name}. "
                       f"Include: sticky header, glassmorphism backdrop-filter, mobile hamburger menu, "
                       f"slide-in overlay, link hover transitions. Use {theme} theme colors.",
                "output": "src/components/Navbar.css created",
            },
            {
                "title": "Create Navigation Component",
                "desc": f"Create the JSX component for the Navbar of {name}. "
                       f"Import Navbar.css. Render: logo, nav links with smooth-scroll, "
                       f"CTA button, hamburger toggle for mobile. Use {theme} theme colors.",
                "output": "src/components/Navbar.jsx created",
                "depends_on_prev": True,
            },
        ],
        "footer": [
            {
                "title": "Create Footer Styling",
                "desc": f"Create the CSS file for the Footer of {name}. "
                       f"Include: multi-column grid, link hover transitions, dark background variant, "
                       f"responsive column stacking. Use {theme} theme colors.",
                "output": "src/components/Footer.css created",
            },
            {
                "title": "Create Footer Component",
                "desc": f"Create the JSX component for the Footer of {name}. "
                       f"Import Footer.css. Render: brand logo + tagline, 3 link columns, "
                       f"social icons, copyright bar. Use {theme} theme colors.",
                "output": "src/components/Footer.jsx created",
                "depends_on_prev": True,
            },
        ],
        "responsive layout": [
            {
                "title": "Implement Responsive Layout",
                "desc": f"Review and enhance responsive CSS across ALL components for {name}. "
                       f"Ensure navigation collapses on mobile (<768px), grids stack vertically, "
                       f"typography scales, touch targets ≥44px. "
                       f"Breakpoints: 375px, 768px, 1024px, 1280px.",
                "output": "All CSS files updated with responsive breakpoints",
            },
        ],
        "dashboard": [
            {
                "title": "Create Dashboard Page Styling",
                "desc": f"Create the CSS file for the Dashboard page of {name}. "
                       f"Include: KPI card grid, chart placeholder area, sidebar layout, "
                       f"card shadows, entrance animations. Use {theme} theme colors.",
                "output": "src/pages/Dashboard.css created",
            },
            {
                "title": "Create Dashboard Page Component",
                "desc": f"Create the JSX component for the Dashboard page of {name}. "
                       f"Import Dashboard.css. Render: 4 KPI stat cards with icons and trend indicators, "
                       f"chart/data visualization area, recent activity panel. "
                       f"Include realistic mock data for the {theme} domain.",
                "output": "src/pages/Dashboard.jsx created",
                "depends_on_prev": True,
            },
        ],
        "user interface": [
            {
                "title": "Create Core UI Component Styles",
                "desc": f"Create a shared CSS file for reusable UI components (Button, Card, Input, Modal) for {name}. "
                       f"Include: consistent border-radius, shadows, focus states, transitions. Use {theme} theme colors.",
                "output": "src/components/ui/ui.css created",
            },
            {
                "title": "Create Core UI Components",
                "desc": f"Create reusable JSX components: Button, Card, Input, Modal for {name}. "
                       f"Import ui.css. Each component should accept props for variants (primary, secondary, outlined).",
                "output": "src/components/ui/index.jsx created",
                "depends_on_prev": True,
            },
        ],
        "data display": [
            {
                "title": "Create Data Display Styling",
                "desc": f"Create the CSS file for the DataTable component of {name}. "
                       f"Include: table layout, header styling, row hover, sort indicators, responsive scroll.",
                "output": "src/components/DataTable.css created",
            },
            {
                "title": "Create Data Display Component",
                "desc": f"Create the JSX component for a sortable, filterable DataTable for {name}. "
                       f"Import DataTable.css. Render: column headers with sort toggles, rows, filter bar.",
                "output": "src/components/DataTable.jsx created",
                "depends_on_prev": True,
            },
        ],
        "settings": [
            {
                "title": "Create Settings Page Styling",
                "desc": f"Create the CSS file for the Settings page of {name}. "
                       f"Include: form sections, toggle switches, save button styling.",
                "output": "src/pages/Settings.css created",
            },
            {
                "title": "Create Settings Page Component",
                "desc": f"Create the JSX component for the Settings page of {name}. "
                       f"Import Settings.css. Render: preference controls grouped in sections with save button.",
                "output": "src/pages/Settings.jsx created",
                "depends_on_prev": True,
            },
        ],
        "search": [
            {
                "title": "Create Search Styling",
                "desc": f"Create the CSS file for the SearchBar component of {name}. "
                       f"Include: input with icon, dropdown results, hover states.",
                "output": "src/components/SearchBar.css created",
            },
            {
                "title": "Create Search Component",
                "desc": f"Create the JSX component for a search bar with filtering and results for {name}. "
                       f"Import SearchBar.css.",
                "output": "src/components/SearchBar.jsx created",
                "depends_on_prev": True,
            },
        ],
        "features section": [
            {
                "title": "Create Features Section Styling",
                "desc": f"Create the CSS file for the Features section of {name}. "
                       f"Include: responsive card grid (1/2/3 columns), card hover lift, "
                       f"icon styling, staggered fadeIn keyframes, rounded corners and shadows. "
                       f"Use {theme} theme colors.",
                "output": "src/components/Features.css created",
            },
            {
                "title": "Create Features Section Component",
                "desc": f"Create the JSX component for the Features section of {name}. "
                       f"Import Features.css. Render: 4-6 feature cards with icons (Unicode emoji), "
                       f"bold titles, descriptive text. Use realistic feature names for the {theme} domain.",
                "output": "src/components/Features.jsx created",
                "depends_on_prev": True,
            },
        ],
        "call to action": [
            {
                "title": "Create CTA Section Styling",
                "desc": f"Create the CSS file for the CTA section of {name}. "
                       f"Include: gradient background, centered layout, button scale + shadow hover, "
                       f"subtle background animation. Use {theme} theme colors.",
                "output": "src/components/CTA.css created",
            },
            {
                "title": "Create CTA Section Component",
                "desc": f"Create the JSX component for the Call To Action section of {name}. "
                       f"Import CTA.css. Render: large headline, subtext, prominent animated button.",
                "output": "src/components/CTA.jsx created",
                "depends_on_prev": True,
            },
        ],
        "testimonials": [
            {
                "title": "Create Testimonials Styling",
                "desc": f"Create the CSS file for the Testimonials section of {name}. "
                       f"Include: responsive card grid, quote styling with large quotation marks, "
                       f"avatar circles with gradient, staggered scaleIn animation. Use {theme} theme colors.",
                "output": "src/components/Testimonials.css created",
            },
            {
                "title": "Create Testimonials Component",
                "desc": f"Create the JSX component for the Testimonials section of {name}. "
                       f"Import Testimonials.css. Render: 3+ review cards with quote, reviewer name, "
                       f"role/company, avatar initial. Use realistic testimonial content for the {theme} domain.",
                "output": "src/components/Testimonials.jsx created",
                "depends_on_prev": True,
            },
        ],
        "product catalog": [
            {
                "title": "Create Product Catalog Styling",
                "desc": f"Create the CSS file for the ProductCatalog component of {name}. "
                       f"Include: product card grid, image placeholder, price styling, hover effects.",
                "output": "src/components/ProductCatalog.css created",
            },
            {
                "title": "Create Product Catalog Component",
                "desc": f"Create the JSX component for the ProductCatalog of {name}. "
                       f"Import ProductCatalog.css. Render: product grid with cards showing image area, "
                       f"name, price, and action button.",
                "output": "src/components/ProductCatalog.jsx created",
                "depends_on_prev": True,
            },
        ],
        "product detail": [
            {
                "title": "Create Product Detail Styling",
                "desc": f"Create the CSS file for the ProductDetail page of {name}. "
                       f"Include: two-column layout (image + info), price styling, add-to-cart button.",
                "output": "src/pages/ProductDetail.css created",
            },
            {
                "title": "Create Product Detail Page",
                "desc": f"Create the JSX component for the ProductDetail page of {name}. "
                       f"Import ProductDetail.css. Render: product image, description, pricing, add-to-cart.",
                "output": "src/pages/ProductDetail.jsx created",
                "depends_on_prev": True,
            },
        ],
        "shopping cart": [
            {
                "title": "Create Shopping Cart Styling",
                "desc": f"Create the CSS file for the Cart component of {name}. "
                       f"Include: item list, quantity controls, totals section, checkout button styling.",
                "output": "src/components/Cart.css created",
            },
            {
                "title": "Create Shopping Cart Component",
                "desc": f"Create the JSX component for the shopping Cart of {name}. "
                       f"Import Cart.css. Render: item list with quantities, totals, checkout button.",
                "output": "src/components/Cart.jsx created",
                "depends_on_prev": True,
            },
        ],
        "checkout": [
            {
                "title": "Create Checkout Page Styling",
                "desc": f"Create the CSS file for the Checkout page of {name}. "
                       f"Include: form sections, payment summary, order confirmation styling.",
                "output": "src/pages/Checkout.css created",
            },
            {
                "title": "Create Checkout Page Component",
                "desc": f"Create the JSX component for the Checkout page of {name}. "
                       f"Import Checkout.css. Render: shipping form, payment summary, order confirmation.",
                "output": "src/pages/Checkout.jsx created",
                "depends_on_prev": True,
            },
        ],
        "image gallery": [
            {
                "title": "Create Gallery Styling",
                "desc": f"Create the CSS file for the Gallery component of {name}. "
                       f"Include: masonry/grid layout, lightbox overlay, image hover zoom.",
                "output": "src/components/Gallery.css created",
            },
            {
                "title": "Create Gallery Component",
                "desc": f"Create the JSX component for an image Gallery with grid layout and lightbox for {name}. "
                       f"Import Gallery.css.",
                "output": "src/components/Gallery.jsx created",
                "depends_on_prev": True,
            },
        ],
        "article list": [
            {
                "title": "Create Article List Styling",
                "desc": f"Create the CSS file for the ArticleList component of {name}. "
                       f"Include: card layout, excerpt truncation, date styling, hover effects.",
                "output": "src/components/ArticleList.css created",
            },
            {
                "title": "Create Article List Component",
                "desc": f"Create the JSX component for a blog/article list for {name}. "
                       f"Import ArticleList.css. Render: cards with title, excerpt, date, read-more link.",
                "output": "src/components/ArticleList.jsx created",
                "depends_on_prev": True,
            },
        ],
        "article detail": [
            {
                "title": "Create Article Detail Styling",
                "desc": f"Create the CSS file for the ArticleDetail page of {name}. "
                       f"Include: article content typography, author info, related articles grid.",
                "output": "src/pages/ArticleDetail.css created",
            },
            {
                "title": "Create Article Detail Page",
                "desc": f"Create the JSX component for the ArticleDetail page of {name}. "
                       f"Import ArticleDetail.css. Render: full article content, author info, related articles.",
                "output": "src/pages/ArticleDetail.jsx created",
                "depends_on_prev": True,
            },
        ],
        "categories": [
            {
                "title": "Create Categories Styling",
                "desc": f"Create the CSS file for the Categories component of {name}. "
                       f"Include: sidebar layout, category item hover, active state, badge count.",
                "output": "src/components/Categories.css created",
            },
            {
                "title": "Create Categories Component",
                "desc": f"Create the JSX component for a categories sidebar/nav for {name}. "
                       f"Import Categories.css. Render: category list with active state highlighting.",
                "output": "src/components/Categories.jsx created",
                "depends_on_prev": True,
            },
        ],
        "metrics overview": [
            {
                "title": "Create Metrics Overview Styling",
                "desc": f"Create the CSS file for the MetricsOverview component of {name}. "
                       f"Include: stat card grid, trend indicator styling, number formatting.",
                "output": "src/components/MetricsOverview.css created",
            },
            {
                "title": "Create Metrics Overview Component",
                "desc": f"Create the JSX component for a metrics dashboard with stat cards for {name}. "
                       f"Import MetricsOverview.css. Render: stat cards with icons, numbers, trends.",
                "output": "src/components/MetricsOverview.jsx created",
                "depends_on_prev": True,
            },
        ],
        "data tables": [
            {
                "title": "Create Data Tables Styling",
                "desc": f"Create the CSS file for the DataTable component of {name}. "
                       f"Include: table layout, sortable headers, row hover, filter bar, responsive scroll.",
                "output": "src/components/DataTable.css created",
            },
            {
                "title": "Create Data Tables Component",
                "desc": f"Create the JSX component for sortable, filterable data tables for {name}. "
                       f"Import DataTable.css.",
                "output": "src/components/DataTable.jsx created",
                "depends_on_prev": True,
            },
        ],
        "charts": [
            {
                "title": "Create Charts Styling",
                "desc": f"Create the CSS file for chart visualisations (bar, line, pie) for {name}. "
                       f"Include: chart container, legend, tooltip, responsive sizing.",
                "output": "src/components/Charts.css created",
            },
            {
                "title": "Create Charts Component",
                "desc": f"Create the JSX component for chart visualisations for {name} dashboard. "
                       f"Import Charts.css. Render: bar/line/pie chart placeholders with CSS-based visuals.",
                "output": "src/components/Charts.jsx created",
                "depends_on_prev": True,
            },
        ],
        "filters": [
            {
                "title": "Create Filter Controls Styling",
                "desc": f"Create the CSS file for filter controls (dropdowns, date pickers, search) for {name}. "
                       f"Include: dropdown styling, input focus states, button group layout.",
                "output": "src/components/Filters.css created",
            },
            {
                "title": "Create Filter Controls Component",
                "desc": f"Create the JSX component for filter UI with dropdowns, date pickers, and search for {name}. "
                       f"Import Filters.css.",
                "output": "src/components/Filters.jsx created",
                "depends_on_prev": True,
            },
        ],
        "projects showcase": [
            {
                "title": "Create Projects Showcase Styling",
                "desc": f"Create the CSS file for the ProjectsShowcase component of {name}. "
                       f"Include: card grid, image placeholder, overlay hover, detail link styling.",
                "output": "src/components/ProjectsShowcase.css created",
            },
            {
                "title": "Create Projects Showcase Component",
                "desc": f"Create the JSX component for a portfolio/projects grid for {name}. "
                       f"Import ProjectsShowcase.css. Render: project cards with image area, title, description, link.",
                "output": "src/components/ProjectsShowcase.jsx created",
                "depends_on_prev": True,
            },
        ],
        "skills section": [
            {
                "title": "Create Skills Section Styling",
                "desc": f"Create the CSS file for the Skills section of {name}. "
                       f"Include: progress bar styling, badge layout, animation for progress fill.",
                "output": "src/components/Skills.css created",
            },
            {
                "title": "Create Skills Section Component",
                "desc": f"Create the JSX component for a skills display with progress bars or badges for {name}. "
                       f"Import Skills.css.",
                "output": "src/components/Skills.jsx created",
                "depends_on_prev": True,
            },
        ],
        "menu section": [
            {
                "title": "Create Menu Section Styling",
                "desc": f"Create the CSS file for the MenuSection of {name}. "
                       f"Include: category tab styling, item card grid (1/2/3 col responsive), "
                       f"hover lift animations, price styling. Use {theme} theme colors.",
                "output": "src/components/MenuSection.css created",
            },
            {
                "title": "Create Menu Section Component",
                "desc": f"Create the JSX component for the MenuSection of {name}. "
                       f"Import MenuSection.css. Render: category tabs at top, grid of item cards "
                       f"(name, description, price, decorative element). "
                       f"Use realistic menu items for the {theme} domain.",
                "output": "src/components/MenuSection.jsx created",
                "depends_on_prev": True,
            },
        ],
    }

    # ── Build tasks from the list-based feature map ───────────────────────
    seen = set()
    for feature in features:
        key = feature.lower().strip()
        if key in seen:
            continue
        seen.add(key)

        mapping = _feature_map.get(key)
        if mapping:
            # mapping is a list of sequential micro-tasks
            prev_title = "Create Theme Variables and Global Styles"
            for micro in mapping:
                deps = [prev_title] if micro.get("depends_on_prev") else ["Create Theme Variables and Global Styles"]
                tasks.append(_task(
                    micro["title"],
                    micro["desc"],
                    "frontend",
                    micro["output"],
                    dependencies=deps,
                ))
                prev_title = micro["title"]
        else:
            # Generic feature task (single file)
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
- CRITICAL RULE: ONE FILE PER TASK. A task must NEVER require writing both a .jsx and a .css file.
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

        # Circuit breaker to enforce ONE FILE PER TASK
        refined = []
        for t in llm_tasks:
            output = t.get("expected_output", "")
            if ".jsx" in output.lower() and ".css" in output.lower():
                css_title = t.get("title", "Task").replace("Component", "Styling").replace("Create ", "Create Styling for ")
                jsx_title = t.get("title", "Task")
                
                # CSS Task
                css_t = deepcopy(t)
                css_t["title"] = css_title
                css_t["expected_output"] = output.replace(".jsx", "").replace("and", "").strip()
                refined.append(css_t)
                
                # JSX Task
                jsx_t = deepcopy(t)
                jsx_t["title"] = jsx_title
                jsx_t["expected_output"] = output.replace(".css", "").replace("and", "").strip()
                jsx_t["dependencies"] = [css_title] + t.get("dependencies", [])
                refined.append(jsx_t)
            else:
                refined.append(t)
        llm_tasks = refined

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

            # Force LLM-augmented decomposition (template routing disabled)
            atomic_tasks = _llm_decompose(title, description, spec)
            logger.info("LLM decomposed '%s' into %d atomic tasks", title, len(atomic_tasks))

            parent_epic = coarse_task.get("epic")
            parent_feature = coarse_task.get("feature")
            parent_story = coarse_task.get("story")
            parent_ac = coarse_task.get("acceptance_criteria")
            parent_context = coarse_task.get("estimated_context")
            parent_meta = coarse_task.get("engineering_metadata") or {}

            for t in atomic_tasks:
                if not t.get("epic"):
                    t["epic"] = parent_epic or "Frontend Infrastructure & UI"
                if not t.get("feature"):
                    t["feature"] = parent_feature or "Core User Interface"
                if not t.get("story"):
                    t["story"] = parent_story or t["title"]
                if not t.get("acceptance_criteria") or t["acceptance_criteria"] == [f"Verify {t['title']} works correctly."]:
                    t["acceptance_criteria"] = parent_ac or [f"Verify {t['title']} works correctly."]
                if not t.get("complexity"):
                    t["complexity"] = "S"
                if not t.get("estimated_context"):
                    t["estimated_context"] = parent_context or ["spec.json"]
                if not t.get("engineering_metadata"):
                    t["engineering_metadata"] = parent_meta or {"layer": "FE", "estimated_files_count": 1}

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
            for t in new_features:
                if not t.get("epic"):
                    t["epic"] = "Frontend Infrastructure & UI"
                if not t.get("feature"):
                    t["feature"] = t["title"].replace("Create ", "").replace(" Component", "")
                if not t.get("story"):
                    t["story"] = f"Implement {t['title']}"
                if not t.get("acceptance_criteria") or t["acceptance_criteria"] == [f"Verify {t['title']} works correctly."]:
                    t["acceptance_criteria"] = [f"Successfully implement {t['title']}", "Verify responsive styling"]
                if not t.get("complexity"):
                    t["complexity"] = "S"
                if not t.get("estimated_context"):
                    t["estimated_context"] = ["spec.json", "src/App.jsx"]
                if not t.get("engineering_metadata"):
                    t["engineering_metadata"] = {"layer": "FE", "estimated_files_count": 2}

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

        # ── Clean up dangling dependencies & assign UIDs ──────────────
        valid_titles = {t["title"] for t in sorted_tasks}
        title_to_uid = {}
        layer_counters: dict[str, int] = {}

        for task in sorted_tasks:
            task["dependencies"] = [d for d in task.get("dependencies", []) if d in valid_titles]
            meta = task.get("engineering_metadata") or {}
            layer = meta.get("layer", "FE")
            count = layer_counters.get(layer, 0) + 1
            layer_counters[layer] = count
            uid = f"TASK-{layer}-{count:03d}"
            task["task_uid"] = uid
            title_to_uid[task["title"]] = uid

        # Update context_dependencies to use UIDs instead of titles
        for task in sorted_tasks:
            task["context_dependencies"] = [
                title_to_uid[dep_title] for dep_title in task["dependencies"] if dep_title in title_to_uid
            ]

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
