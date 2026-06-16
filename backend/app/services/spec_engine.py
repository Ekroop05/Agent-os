"""
Project Specification Engine — the single source of truth for every build.

Generates, persists, and reads `.agentos/spec.json`.
Every agent reads from spec.json.  Requirements are never rebuilt from
chat history or inferred after the build begins.
"""

from __future__ import annotations

import json
import logging
import os
from copy import deepcopy

logger = logging.getLogger("spec_engine")

# ── Theme Context Mapping ─────────────────────────────────────────────────
# Maps themes to concrete implementation guidance so the Builder knows
# HOW to implement the theme, not just WHAT it is.

THEME_CONTEXT: dict[str, dict] = {
    "Superhero": {
        "color_palette": "Dark navy (#0a1628), crimson red (#e23636), gold (#f5c518), silver (#c0c0c0)",
        "tone": "Bold, heroic, action-oriented, cinematic",
        "content_domain": "Superheroes, powers, missions, team rosters, epic battles",
        "suggested_sections": ["Hero Banner with dramatic imagery", "Character/Hero Showcase Cards", "Team Roster", "Mission Timeline", "Powers & Abilities"],
        "style_keywords": ["dramatic gradients", "bold typography", "comic-book energy", "metallic accents"],
    },
    "Space / Sci-Fi": {
        "color_palette": "Deep space black (#0b0d17), nebula purple (#7b2ff7), cyan glow (#00d4ff), starlight white (#e8e8e8)",
        "tone": "Futuristic, mysterious, awe-inspiring",
        "content_domain": "Planets, galaxies, space exploration, technology, stars",
        "suggested_sections": ["Cosmic Hero Banner", "Planet/Galaxy Explorer", "Mission Control Dashboard", "Star Map", "Discovery Feed"],
        "style_keywords": ["glowing borders", "particle effects", "dark backgrounds", "neon accents"],
    },
    "Anime / Manga": {
        "color_palette": "Sakura pink (#ff6b9d), midnight blue (#1a1a2e), vivid purple (#c061cb), warm white (#faf0e6)",
        "tone": "Vibrant, energetic, expressive, dynamic",
        "content_domain": "Anime characters, manga series, episodes, genres, studios",
        "suggested_sections": ["Featured Anime Banner", "Character Gallery", "Genre Browser", "Trending Series", "Watch List"],
        "style_keywords": ["vibrant gradients", "rounded cards", "anime-style typography", "dynamic layouts"],
    },
    "Gaming / Esports": {
        "color_palette": "Dark charcoal (#1a1a2e), neon green (#00ff88), electric blue (#00b4d8), hot pink (#ff006e)",
        "tone": "Competitive, high-energy, immersive",
        "content_domain": "Games, tournaments, players, teams, leaderboards, streams",
        "suggested_sections": ["Featured Game Banner", "Tournament Brackets", "Player Profiles", "Leaderboard", "Live Streams"],
        "style_keywords": ["neon glow effects", "dark mode", "sharp edges", "RGB accents"],
    },
    "Fitness / Health": {
        "color_palette": "Energetic orange (#ff6b35), deep teal (#00b4d8), dark slate (#2d3436), clean white (#f8f9fa)",
        "tone": "Motivational, energetic, clean, empowering",
        "content_domain": "Workouts, exercises, nutrition, progress tracking, wellness",
        "suggested_sections": ["Motivational Hero Banner", "Workout Cards", "Progress Tracker", "Nutrition Guide", "Trainer Profiles"],
        "style_keywords": ["bold typography", "rounded elements", "progress bars", "energy gradients"],
    },
    "Food / Culinary": {
        "color_palette": "Warm amber (#f59e0b), rich brown (#78350f), cream (#fefce8), olive green (#65a30d)",
        "tone": "Warm, inviting, artisanal, delicious",
        "content_domain": "Recipes, menus, ingredients, chefs, restaurants, food culture",
        "suggested_sections": ["Featured Dish Hero", "Menu Section", "Chef's Special", "About the Kitchen", "Reservation/Contact"],
        "style_keywords": ["warm tones", "food photography emphasis", "elegant typography", "cozy atmosphere"],
    },
    "Music": {
        "color_palette": "Electric violet (#8b5cf6), midnight (#111827), hot magenta (#ec4899), silver (#9ca3af)",
        "tone": "Rhythmic, expressive, bold, creative",
        "content_domain": "Artists, albums, tracks, concerts, genres, playlists",
        "suggested_sections": ["Now Playing Hero", "Artist Showcase", "Album Grid", "Concert Calendar", "Genre Explorer"],
        "style_keywords": ["waveform visuals", "dark backgrounds", "vinyl/record motifs", "equalizer animations"],
    },
    "Travel": {
        "color_palette": "Ocean blue (#0077b6), sunset orange (#fb8500), sandy beige (#f4e1c1), forest green (#2d6a4f)",
        "tone": "Adventurous, inspiring, wanderlust, free-spirited",
        "content_domain": "Destinations, trips, itineraries, culture, landscapes",
        "suggested_sections": ["Destination Hero Banner", "Popular Destinations Grid", "Travel Itineraries", "Photo Gallery", "Travel Tips"],
        "style_keywords": ["panoramic imagery", "warm gradients", "map elements", "postcard aesthetic"],
    },
    "Education": {
        "color_palette": "Royal blue (#1d4ed8), fresh green (#22c55e), warm yellow (#eab308), clean white (#f8fafc)",
        "tone": "Friendly, clear, structured, encouraging",
        "content_domain": "Courses, lessons, students, instructors, progress, certifications",
        "suggested_sections": ["Learning Hero Banner", "Course Catalog", "Instructor Profiles", "Student Dashboard", "Progress Tracker"],
        "style_keywords": ["clean layouts", "card-based design", "progress indicators", "friendly icons"],
    },
    "Finance": {
        "color_palette": "Deep navy (#0f172a), emerald green (#10b981), gold (#f59e0b), cool gray (#6b7280)",
        "tone": "Professional, trustworthy, precise, authoritative",
        "content_domain": "Markets, portfolios, transactions, analytics, financial planning",
        "suggested_sections": ["Market Overview Hero", "Portfolio Dashboard", "Transaction History", "Analytics Charts", "Financial Tools"],
        "style_keywords": ["data visualizations", "clean grids", "trust signals", "professional typography"],
    },
    "Healthcare": {
        "color_palette": "Medical blue (#0ea5e9), healing green (#22c55e), soft white (#f0f9ff), warm gray (#9ca3af)",
        "tone": "Caring, trustworthy, clean, professional",
        "content_domain": "Patients, doctors, appointments, health records, wellness",
        "suggested_sections": ["Welcome Hero", "Services Overview", "Doctor Profiles", "Appointment Booking", "Health Resources"],
        "style_keywords": ["clean minimal design", "rounded corners", "calming colors", "accessibility-first"],
    },
    "Fashion": {
        "color_palette": "Elegant black (#111111), rose gold (#b76e79), off-white (#faf9f6), champagne (#f7e7ce)",
        "tone": "Elegant, trendy, aspirational, luxurious",
        "content_domain": "Collections, designers, lookbooks, trends, styling",
        "suggested_sections": ["Lookbook Hero", "Collection Showcase", "Designer Spotlight", "Trend Feed", "Style Guide"],
        "style_keywords": ["editorial layout", "large imagery", "luxury typography", "minimal UI"],
    },
    "Technology": {
        "color_palette": "Tech blue (#3b82f6), dark surface (#0f172a), accent cyan (#06b6d4), light gray (#e2e8f0)",
        "tone": "Innovative, forward-thinking, clean, precise",
        "content_domain": "Products, features, integrations, documentation, team",
        "suggested_sections": ["Product Hero Banner", "Feature Showcase", "Integration Grid", "Pricing Table", "About/Team"],
        "style_keywords": ["glassmorphism", "subtle gradients", "monospace accents", "geometric shapes"],
    },
    "Nature / Environment": {
        "color_palette": "Forest green (#166534), earth brown (#92400e), sky blue (#38bdf8), leaf (#86efac)",
        "tone": "Serene, organic, grounding, eco-conscious",
        "content_domain": "Wildlife, conservation, landscapes, sustainability, ecology",
        "suggested_sections": ["Nature Hero Banner", "Wildlife Gallery", "Conservation Projects", "Eco Tips", "Photo Stories"],
        "style_keywords": ["organic shapes", "nature photography", "earthy tones", "flowing layouts"],
    },
    "Art / Gallery": {
        "color_palette": "Gallery white (#fafafa), accent black (#1a1a1a), warm gold (#d4a574), muted rose (#c9ada7)",
        "tone": "Sophisticated, contemplative, curated, expressive",
        "content_domain": "Artworks, artists, exhibitions, collections, techniques",
        "suggested_sections": ["Featured Exhibition Hero", "Artwork Grid", "Artist Profiles", "Virtual Gallery", "Events Calendar"],
        "style_keywords": ["white space", "gallery-style grids", "elegant typography", "minimal chrome"],
    },
    "Sports": {
        "color_palette": "Stadium green (#15803d), energy red (#dc2626), dark navy (#1e3a5f), white (#ffffff)",
        "tone": "Exciting, competitive, passionate, dynamic",
        "content_domain": "Teams, matches, scores, players, statistics, standings",
        "suggested_sections": ["Match Day Hero", "Live Scores", "Team Roster", "League Standings", "Highlights"],
        "style_keywords": ["bold numbers", "score-board aesthetic", "action imagery", "stat cards"],
    },
    "Pets / Animals": {
        "color_palette": "Warm orange (#f97316), soft brown (#a16207), sky blue (#7dd3fc), cream (#fffbeb)",
        "tone": "Playful, warm, adorable, friendly",
        "content_domain": "Pets, breeds, adoption, care tips, stories, photos",
        "suggested_sections": ["Hero Banner with pet imagery", "Pet Gallery", "Adoption Center", "Care Guide", "Community Stories"],
        "style_keywords": ["rounded shapes", "paw prints", "warm colors", "playful typography"],
    },
    "Real Estate": {
        "color_palette": "Navy blue (#1e3a5f), warm gold (#d4a574), clean white (#f8fafc), accent green (#059669)",
        "tone": "Professional, trustworthy, aspirational, elegant",
        "content_domain": "Properties, listings, neighborhoods, agents, market data",
        "suggested_sections": ["Featured Listings Hero", "Property Search", "Neighborhood Guide", "Agent Profiles", "Market Insights"],
        "style_keywords": ["property cards with images", "map integration", "clean filters", "trust badges"],
    },
    "News / Media": {
        "color_palette": "Ink black (#0a0a0a), paper white (#fafafa), accent red (#dc2626), medium gray (#6b7280)",
        "tone": "Authoritative, timely, clear, informative",
        "content_domain": "Articles, breaking news, opinions, reporters, categories",
        "suggested_sections": ["Breaking News Hero", "Top Stories Grid", "Category Sections", "Opinion Columns", "Trending Topics"],
        "style_keywords": ["newspaper layout", "serif headings", "clean typography", "content-dense"],
    },
    "Movies / Cinema": {
        "color_palette": "Theater black (#0a0a0a), popcorn gold (#f59e0b), spotlight white (#fafafa), velvet red (#991b1b)",
        "tone": "Cinematic, dramatic, entertaining, immersive",
        "content_domain": "Movies, reviews, actors, genres, showtimes, trailers",
        "suggested_sections": ["Now Showing Hero", "Movie Cards Grid", "Actor Profiles", "Genre Browser", "Coming Soon"],
        "style_keywords": ["dark backgrounds", "poster-style cards", "dramatic typography", "trailer embeds"],
    },
}

# ── Default feature sets by project type ──────────────────────────────────

_DEFAULT_FEATURES: dict[str, list[str]] = {
    "Website": ["Hero Section", "Navigation", "About Section", "Contact Section", "Footer", "Responsive Layout"],
    "Web Application": ["Navigation", "Dashboard", "User Interface", "Data Display", "Settings", "Responsive Layout"],
    "Dashboard": ["Navigation", "Metrics Overview", "Data Tables", "Charts", "Filters", "Responsive Layout"],
    "Landing Page": ["Hero Section", "Features Section", "Call to Action", "Testimonials", "Footer"],
    "Portfolio Website": ["Hero Section", "Projects Showcase", "Skills Section", "About Me", "Contact Form", "Footer"],
    "Blog": ["Hero Section", "Article List", "Article Detail", "Categories", "Search", "Footer"],
    "E-Commerce Platform": ["Hero Section", "Product Catalog", "Product Detail", "Shopping Cart", "Checkout", "Navigation", "Footer"],
}


class SpecEngine:
    """Generates and manages the project specification (spec.json)."""

    def generate_spec(self, state: dict) -> dict:
        """Create a spec from the architect conversation state.

        This is called once after architecture generation / approval and
        becomes the immutable source of truth for the build pipeline.
        """
        from app.services.project_name_generator import generate_name, sanitize_name

        # ── Resolve project name ──────────────────────────────────────
        raw_name = state.get("project_name") or ""
        name = sanitize_name(raw_name)
        if not name:
            name = generate_name(
                theme=state.get("theme"),
                project_type=state.get("project_type"),
                purpose=state.get("purpose"),
            )

        # ── Resolve features ──────────────────────────────────────────
        user_features = list(state.get("core_features") or [])
        project_type = state.get("project_type") or "Website"

        # Merge user-requested features with type defaults (user features first)
        default_features = _DEFAULT_FEATURES.get(project_type, _DEFAULT_FEATURES["Website"])
        merged_features = list(dict.fromkeys(user_features + default_features))

        # ── Resolve theme context ─────────────────────────────────────
        theme = state.get("theme") or ""
        theme_context = self._resolve_theme_context(theme)

        # ── Build spec ────────────────────────────────────────────────
        backend = state.get("backend")
        database = state.get("database")
        authentication = state.get("authentication")

        spec = {
            "project_name": name,
            "project_type": project_type,
            "theme": theme or "General",
            "purpose": state.get("purpose") or "General",
            "target_users": state.get("target_users") or "General Visitors",
            "frontend": state.get("frontend") or "React + Vite",
            "backend": backend if backend is not None else False,
            "database": database if database is not None else False,
            "authentication": authentication if authentication is not None else False,
            "deployment": state.get("deployment") or "No Deployment",
            "required_features": merged_features,
            "quality_target": 85,
            "theme_context": theme_context,
        }

        return spec

    def write_spec(self, workspace_path: str, spec: dict) -> str:
        """Write spec.json to .agentos/ directory.  Returns the file path."""
        spec_path = os.path.join(
            workspace_path.replace("/", os.sep), ".agentos", "spec.json"
        )
        os.makedirs(os.path.dirname(spec_path), exist_ok=True)

        with open(spec_path, "w", encoding="utf-8") as f:
            json.dump(spec, f, indent=2, default=str)

        logger.info("Wrote spec.json to %s", spec_path)
        return spec_path

    def read_spec(self, workspace_path: str) -> dict | None:
        """Read spec.json from .agentos/ directory.  Returns None if missing."""
        spec_path = os.path.join(
            workspace_path.replace("/", os.sep), ".agentos", "spec.json"
        )
        if not os.path.exists(spec_path):
            return None

        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read spec.json: %s", e)
            return None

    def validate_spec(self, spec: dict) -> list[str]:
        """Validate that a spec has all required fields.  Returns list of issues."""
        issues = []
        required = ["project_name", "project_type", "required_features"]

        for field in required:
            if not spec.get(field):
                issues.append(f"Missing required field: {field}")

        if spec.get("required_features") and not isinstance(spec["required_features"], list):
            issues.append("required_features must be a list")

        name = spec.get("project_name", "").lower()
        from app.services.project_name_generator import BLACKLIST
        if name in BLACKLIST:
            issues.append(f"Project name '{spec['project_name']}' is blacklisted")

        return issues

    def enrich_task_description(self, task_title: str, task_description: str, spec: dict) -> str:
        """Inject spec context into a task description so the Builder has full context."""
        theme = spec.get("theme", "General")
        theme_ctx = spec.get("theme_context", {})

        context_block = "\n".join([
            "",
            "── Project Context ──────────────────────────────────────",
            f"  Project: {spec.get('project_name', 'Unknown')}",
            f"  Theme: {theme}",
            f"  Purpose: {spec.get('purpose', 'General')}",
            f"  Target Users: {spec.get('target_users', 'General Visitors')}",
            f"  Frontend: {spec.get('frontend', 'React + Vite')}",
            f"  Backend: {spec.get('backend', False)}",
            f"  Required Features: {', '.join(spec.get('required_features', []))}",
        ])

        if theme_ctx:
            context_block += "\n" + "\n".join([
                f"  Color Palette: {theme_ctx.get('color_palette', 'N/A')}",
                f"  Tone: {theme_ctx.get('tone', 'N/A')}",
                f"  Content Domain: {theme_ctx.get('content_domain', 'N/A')}",
            ])

        context_block += "\n─────────────────────────────────────────────────────────"

        return f"{task_description}\n{context_block}"

    # ── Internal helpers ──────────────────────────────────────────────────

    def _resolve_theme_context(self, theme: str) -> dict:
        """Look up concrete implementation guidance for a theme."""
        if not theme:
            return {}

        # Exact match
        if theme in THEME_CONTEXT:
            return deepcopy(THEME_CONTEXT[theme])

        # Partial match (e.g. user says "Marvel" and we have "Superhero")
        theme_lower = theme.lower()
        for key, context in THEME_CONTEXT.items():
            if theme_lower in key.lower() or key.lower() in theme_lower:
                return deepcopy(context)

        # Content-domain keyword search
        for key, context in THEME_CONTEXT.items():
            domain = context.get("content_domain", "").lower()
            if theme_lower in domain:
                return deepcopy(context)

        # No match — return a generic context
        return {
            "color_palette": "Professional blue (#3b82f6), dark surface (#0f172a), accent (#06b6d4), light gray (#e2e8f0)",
            "tone": "Modern, clean, professional",
            "content_domain": theme,
            "suggested_sections": ["Hero Section", "Content Showcase", "Features", "About", "Contact"],
            "style_keywords": ["clean design", "modern typography", "subtle gradients", "responsive layout"],
        }


# ── Singleton ─────────────────────────────────────────────────────────────

spec_engine = SpecEngine()
