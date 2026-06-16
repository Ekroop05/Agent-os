"""
Project Name Generator — creates memorable project names.

When the user doesn't provide a project name, this module synthesizes one
from the theme, project type, and purpose.  The goal: every generated project
should feel like a real product, never "Generated Project" or "Website".
"""

from __future__ import annotations

import random

# ── Blacklisted standalone names ──────────────────────────────────────────
# These are never acceptable as the *entire* project name.

BLACKLIST = {
    "generated project",
    "website",
    "application",
    "project",
    "untitled project",
    "untitled",
    "web app",
    "app",
    "my project",
    "new project",
}

# ── Theme → creative name mapping ────────────────────────────────────────
# Each theme key maps to a list of candidate names.  A random one is picked
# so successive builds feel distinct.

_THEME_NAMES: dict[str, list[str]] = {
    # Pop culture
    "Superhero":           ["Hero Nexus", "Avenger Central", "Cape & Shield", "Hero Forge"],
    "Space / Sci-Fi":      ["Stellar Command", "Nebula Hub", "Cosmos Explorer", "Star Drift"],
    "Anime / Manga":       ["Anime Verse", "Manga Scroll", "Otaku Hub", "Sakura Stream"],
    "Gaming / Esports":    ["Arena Pulse", "Game Vault", "Pixel Arena", "Clutch Zone"],
    "Movies / Cinema":     ["Reel House", "Cinema Scope", "Frame & Story", "Silver Screen"],

    # Lifestyle
    "Fitness / Health":    ["FitPulse", "Iron Core", "Vital Edge", "Peak Form"],
    "Food / Culinary":     ["Midnight Brew", "Flavor Forge", "Spice Trail", "The Pantry"],
    "Music":               ["SoundWave", "Amp House", "Rhythm Lab", "Beat Drop"],
    "Travel":              ["Wanderlust", "Passport Diaries", "Route Atlas", "Horizon Go"],
    "Fashion":             ["Vogue Vault", "Thread Studio", "Style Axis", "Luxe Line"],
    "Pets / Animals":      ["Paw Palace", "Critter Hub", "Furry Friends", "Wild Paws"],

    # Professional
    "Education":           ["Scholar Hub", "LearnPath", "Bright Minds", "EduSphere"],
    "Finance":             ["Ledger Pro", "FinEdge", "Vault Capital", "Mint Board"],
    "Healthcare":          ["MedCore", "Vital Signs", "Care Bridge", "Health Nexus"],
    "Technology":          ["Tech Forge", "Code Nexus", "Innovation Lab", "Dev Pulse"],
    "Real Estate":         ["Nest Finder", "Property Pulse", "Home Atlas", "Estate Hub"],
    "News / Media":        ["Daily Lens", "Press Wire", "Beacon News", "Signal Post"],

    # Creative
    "Nature / Environment": ["Green Pulse", "Earth Canvas", "Wild Root", "Eco Sphere"],
    "Art / Gallery":        ["Canvas House", "Gallery Flux", "Art Prism", "Muse Wall"],
    "Sports":               ["Sport Central", "Match Day", "The Arena", "Game On"],
}

# ── Purpose-based fallback names ──────────────────────────────────────────

_PURPOSE_NAMES: dict[str, list[str]] = {
    "Entertainment":      ["Fun Zone", "Vibe Central", "Play House"],
    "Business":           ["Biz Core", "Enterprise Hub", "Corp Suite"],
    "Personal Showcase":  ["My Portfolio", "Personal Space", "Showcase"],
    "Educational":        ["Learn Hub", "Study Zone", "Academy"],
    "E-Commerce":         ["Shop Front", "Market Place", "Store Hub"],
    "Social / Community": ["Connect Hub", "Community Board", "Social Hive"],
    "Management":         ["Control Panel", "Ops Center", "Manage Pro"],
    "Informational":      ["Info Hub", "Knowledge Base", "Guide Post"],
}

# ── Type-based suffix mapping ─────────────────────────────────────────────

_TYPE_SUFFIXES: dict[str, str] = {
    "Website":               "Site",
    "Web Application":       "App",
    "Dashboard":             "Dashboard",
    "Landing Page":          "Page",
    "Portfolio Website":     "Portfolio",
    "Blog":                  "Blog",
    "E-Commerce Platform":   "Store",
    "Marketplace":           "Market",
    "SaaS Application":      "Platform",
    "API Service":           "API",
    "Mobile Application":    "App",
    "Game":                  "Game",
    "Developer Tool":        "Tools",
    "Platform":              "Platform",
    "Portal":                "Portal",
    "Social Network":        "Network",
    "Forum":                 "Forum",
    "Chat Application":      "Chat",
}


def generate_name(
    theme: str | None = None,
    project_type: str | None = None,
    purpose: str | None = None,
) -> str:
    """Generate a creative project name from available context.

    Priority:
      1. Theme-specific creative name
      2. Purpose-specific creative name
      3. Theme + Type composite  (e.g. "Superhero Website")
      4. Purpose + Type composite (e.g. "Entertainment Hub")
      5. Capitalized type alone   (e.g. "Dashboard")
      6. "New Project" (absolute last resort)
    """

    # 1. Try theme-specific creative name
    if theme:
        # Normalize theme key — the mapping uses the canonical form from _THEME_PATTERNS
        for key, names in _THEME_NAMES.items():
            if key.lower() == theme.lower() or theme.lower() in key.lower():
                return random.choice(names)

    # 2. Try purpose-specific creative name
    if purpose:
        for key, names in _PURPOSE_NAMES.items():
            if key.lower() == purpose.lower() or purpose.lower() in key.lower():
                return random.choice(names)

    # 3. Theme + Type composite
    if theme and project_type:
        theme_word = theme.split(" / ")[0].split(",")[0].strip()
        type_suffix = _TYPE_SUFFIXES.get(project_type, project_type or "Project")
        return f"{theme_word} {type_suffix}"

    # 4. Purpose + Type composite
    if purpose and project_type:
        purpose_word = purpose.split(" / ")[0].strip()
        type_suffix = _TYPE_SUFFIXES.get(project_type, project_type or "Hub")
        return f"{purpose_word} {type_suffix}"

    # 5. Type alone (if it's specific enough)
    if project_type and project_type.lower() not in BLACKLIST:
        return project_type

    # 6. Absolute last resort
    return "New Project"


def sanitize_name(name: str) -> str:
    """Ensure a user-provided or generated name is not on the blacklist.

    If the name is blacklisted, returns an empty string so the caller
    knows to try generation instead.
    """
    if not name:
        return ""
    if name.strip().lower() in BLACKLIST:
        return ""
    return name.strip()
