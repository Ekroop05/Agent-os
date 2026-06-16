"""
Requirement Extractor — runs BEFORE the LLM.

Pure rule-based extraction + inference.  No LLM calls.
Extracts structured requirements from user messages and infers obvious defaults.
"""

from __future__ import annotations

import re

# ── Project type patterns ─────────────────────────────────────────────────

_PROJECT_TYPE_MAP: dict[str, str] = {
    "website": "Website",
    "web site": "Website",
    "web app": "Web Application",
    "webapp": "Web Application",
    "application": "Web Application",
    "dashboard": "Dashboard",
    "landing page": "Landing Page",
    "portfolio": "Portfolio Website",
    "blog": "Blog",
    "e-commerce": "E-Commerce Platform",
    "ecommerce": "E-Commerce Platform",
    "marketplace": "Marketplace",
    "saas": "SaaS Application",
    "api": "API Service",
    "rest api": "API Service",
    "mobile app": "Mobile Application",
    "game": "Game",
    "tool": "Developer Tool",
    "cms": "Content Management System",
    "crm": "CRM System",
    "erp": "ERP System",
    "platform": "Platform",
    "portal": "Portal",
    "social network": "Social Network",
    "forum": "Forum",
    "chat app": "Chat Application",
    "chat application": "Chat Application",
}

# ── Theme patterns ────────────────────────────────────────────────────────

_THEME_PATTERNS: list[tuple[str, str]] = [
    (r"superhero", "Superhero"),
    (r"space|galaxy|cosmic", "Space / Sci-Fi"),
    (r"anime|manga", "Anime / Manga"),
    (r"gaming|esports", "Gaming / Esports"),
    (r"fitness|gym|workout", "Fitness / Health"),
    (r"food|recipe|restaurant|cook", "Food / Culinary"),
    (r"music|band|concert|dj", "Music"),
    (r"travel|vacation|tourism", "Travel"),
    (r"education|school|university|learn", "Education"),
    (r"finance|banking|crypto|stock", "Finance"),
    (r"medical|health|hospital|doctor", "Healthcare"),
    (r"fashion|clothing|style", "Fashion"),
    (r"movie|film|cinema", "Movies / Cinema"),
    (r"nature|wildlife|environment", "Nature / Environment"),
    (r"art|gallery|museum", "Art / Gallery"),
    (r"sport|soccer|football|basketball|cricket", "Sports"),
    (r"tech|startup|innovation", "Technology"),
    (r"pet|dog|cat|animal", "Pets / Animals"),
    (r"real estate|property|housing", "Real Estate"),
    (r"news|magazine|journal", "News / Media"),
]

# ── Purpose patterns ──────────────────────────────────────────────────────

_PURPOSE_PATTERNS: list[tuple[str, str]] = [
    (r"fun|entertainment|enjoy|cool|awesome", "Entertainment"),
    (r"business|professional|corporate|company", "Business"),
    (r"portfolio|showcase|personal", "Personal Showcase"),
    (r"education|learn|teach|course|tutorial", "Educational"),
    (r"sell|shop|buy|purchase|store|product", "E-Commerce"),
    (r"social|community|connect|network", "Social / Community"),
    (r"manage|organize|track|admin", "Management"),
    (r"inform|news|blog|article|content", "Informational"),
]

# ── User patterns ─────────────────────────────────────────────────────────

_USER_PATTERNS: list[tuple[str, str]] = [
    (r"recruiter|employer|hiring", "Recruiters and Employers"),
    (r"student|learner", "Students"),
    (r"developer|programmer|engineer", "Developers"),
    (r"customer|buyer|shopper", "Customers"),
    (r"admin|administrator|manager", "Administrators"),
    (r"visitor|viewer|browser|public|everyone|general|anybody|anyone", "General Visitors"),
    (r"team|employee|staff|internal", "Internal Team"),
    (r"kid|children|child|young", "Children / Young Users"),
    (r"gamer|player", "Gamers"),
    (r"patient|doctor", "Healthcare Users"),
    (r"client", "Clients"),
]

# ── Feature extraction ────────────────────────────────────────────────────

_FEATURE_PATTERNS: list[tuple[str, str]] = [
    (r"login|sign.?in|sign.?up|register|auth", "User Authentication"),
    (r"gallery|image|photo|picture", "Image Gallery"),
    (r"search|filter|find", "Search & Filter"),
    (r"profile|account|settings", "User Profiles"),
    (r"chat|message|inbox", "Real-time Chat"),
    (r"upload|file.?upload", "File Upload"),
    (r"payment|checkout|cart|purchase|buy", "Payments & Checkout"),
    (r"dashboard|analytics|stats|chart", "Dashboard & Analytics"),
    (r"notification|alert|push", "Notifications"),
    (r"comment|review|rating|feedback", "Comments & Reviews"),
    (r"admin|management|panel", "Admin Panel"),
    (r"map|location|geo", "Maps & Location"),
    (r"calendar|schedule|booking|appointment", "Calendar & Scheduling"),
    (r"blog|post|article|write|editor", "Blog / Content Editor"),
    (r"share|social.?share", "Social Sharing"),
    (r"dark.?mode|theme.?switch", "Dark Mode / Theme Switching"),
    (r"responsive|mobile.?friendly", "Responsive Design"),
    (r"detail|details|page|pages", "Detail Pages"),
    (r"hero|heroes|character|characters", "Hero / Character Showcase"),
    (r"list|listing|catalog|catalogue|browse", "Listings / Catalog"),
    (r"video|stream|watch", "Video / Streaming"),
    (r"animation|animated|motion", "Animations"),
    (r"contact|contact.?form|email.?form", "Contact Form"),
]

# ── Tech extraction ───────────────────────────────────────────────────────

_FRONTEND_PATTERNS: dict[str, str] = {
    "react": "React", "vue": "Vue.js", "angular": "Angular",
    "svelte": "Svelte", "next": "Next.js", "nuxt": "Nuxt.js",
    "html": "HTML/CSS/JS", "vanilla": "Vanilla JS",
    "tailwind": "TailwindCSS", "bootstrap": "Bootstrap",
}

_BACKEND_PATTERNS: dict[str, str] = {
    "fastapi": "FastAPI", "flask": "Flask", "django": "Django",
    "express": "Express.js", "node": "Node.js", "spring": "Spring Boot",
    "rails": "Ruby on Rails", "laravel": "Laravel",
    "nest": "NestJS", "go": "Go", "rust": "Rust",
}

_DATABASE_PATTERNS: dict[str, str] = {
    "postgres": "PostgreSQL", "postgresql": "PostgreSQL",
    "mysql": "MySQL", "mongo": "MongoDB", "mongodb": "MongoDB",
    "sqlite": "SQLite", "redis": "Redis", "firebase": "Firebase",
    "supabase": "Supabase", "dynamodb": "DynamoDB",
}

# ── Inference rules ───────────────────────────────────────────────────────

_INFERENCES: list[dict] = [
    # Portfolio → Recruiters, no auth
    {"if_type": "Portfolio Website", "infer": {"target_users": "Recruiters and Employers", "authentication": False, "backend": False, "database": False}},
    # Landing page → minimal
    {"if_type": "Landing Page", "infer": {"target_users": "General Visitors", "authentication": False, "backend": False, "database": False}},
    # Blog → readers
    {"if_type": "Blog", "infer": {"target_users": "General Readers", "authentication": "Optional (for authors)"}},
    # E-Commerce → customers, auth required
    {"if_type": "E-Commerce Platform", "infer": {"target_users": "Customers", "authentication": True, "database": "PostgreSQL"}},
    # Dashboard → internal
    {"if_type": "Dashboard", "infer": {"target_users": "Internal Team", "authentication": True}},
    # API Service → developers
    {"if_type": "API Service", "infer": {"target_users": "Developers", "frontend": False}},
    # Game → gamers
    {"if_type": "Game", "infer": {"target_users": "Gamers", "purpose": "Entertainment"}},

    # Theme-based inference
    {"if_purpose": "Entertainment", "infer": {"target_users": "General Visitors"}},
    {"if_purpose": "E-Commerce", "infer": {"authentication": True, "database": "PostgreSQL"}},
]

# ── Approval detection ────────────────────────────────────────────────────

_APPROVAL_PATTERNS = re.compile(
    r"\b(yes|approve|start|proceed|go ahead|let'?s go|do it|build it|start project|looks good|approved|lgtm|ship it)\b",
    re.IGNORECASE,
)


def _lower(text: str) -> str:
    return text.lower().strip()


class RequirementExtractor:
    """Stateless extractor — call extract() with raw user text, get a dict of updates."""

    def extract(self, message: str, current_state: dict) -> dict:
        """Return a dict of newly extracted fields from the user's message."""
        text = message.strip()
        lowered = _lower(text)
        updates: dict = {}

        # ── Project name ──────────────────────────────────────────────
        if not current_state.get("project_name"):
            name = self._extract_name(text)
            if name:
                updates["project_name"] = name

        # ── Project type ──────────────────────────────────────────────
        if not current_state.get("project_type"):
            for pattern, ptype in _PROJECT_TYPE_MAP.items():
                if pattern in lowered:
                    updates["project_type"] = ptype
                    break

        # ── Theme ─────────────────────────────────────────────────────
        if not current_state.get("theme"):
            for pattern, theme in _THEME_PATTERNS:
                if re.search(pattern, lowered):
                    updates["theme"] = theme
                    break

        # ── Purpose ───────────────────────────────────────────────────
        if not current_state.get("purpose"):
            for pattern, purpose in _PURPOSE_PATTERNS:
                if re.search(pattern, lowered):
                    updates["purpose"] = purpose
                    break

        # ── Target users ──────────────────────────────────────────────
        if not current_state.get("target_users"):
            for pattern, users in _USER_PATTERNS:
                if re.search(pattern, lowered):
                    updates["target_users"] = users
                    break

        # ── Features ──────────────────────────────────────────────────
        new_features = []
        existing = set(current_state.get("core_features") or [])
        for pattern, feature in _FEATURE_PATTERNS:
            if re.search(pattern, lowered) and feature not in existing:
                new_features.append(feature)
        if new_features:
            updates["core_features"] = new_features

        # ── Frontend ──────────────────────────────────────────────────
        if not current_state.get("frontend"):
            for pattern, tech in _FRONTEND_PATTERNS.items():
                if pattern in lowered:
                    updates["frontend"] = tech
                    break

        # ── Backend ───────────────────────────────────────────────────
        if current_state.get("backend") is None:
            # Check for explicit "no backend" signals first
            if re.search(r"\b(no backend|no server|no api|frontend.?only|client.?side.?only|static.?site|static.?only|purely.?client|no server.?side)\b", lowered):
                updates["backend"] = False
            else:
                for pattern, tech in _BACKEND_PATTERNS.items():
                    if pattern in lowered:
                        updates["backend"] = tech
                        break

        # ── Database ──────────────────────────────────────────────────
        if current_state.get("database") is None:
            # Check for explicit "no database" signals first
            if re.search(r"\b(no database|no db|no data.?base|no storage|no persistence)\b", lowered):
                updates["database"] = False
            # Also infer no database when backend is explicitly false
            elif updates.get("backend") is False or current_state.get("backend") is False:
                updates["database"] = False
            else:
                for pattern, tech in _DATABASE_PATTERNS.items():
                    if pattern in lowered:
                        updates["database"] = tech
                        break

        # ── Authentication ────────────────────────────────────────────
        if current_state.get("authentication") is None:
            if re.search(r"\b(no auth|no login|no sign.?up|public|no account)\b", lowered):
                updates["authentication"] = False
            elif re.search(r"\b(auth|login|sign.?up|register|account|user account)\b", lowered):
                updates["authentication"] = True

        # ── Deployment ────────────────────────────────────────────────
        if not current_state.get("deployment"):
            deploy_map = {
                "vercel": "Vercel", "netlify": "Netlify", "aws": "AWS",
                "heroku": "Heroku", "docker": "Docker", "railway": "Railway",
                "fly.io": "Fly.io", "digitalocean": "DigitalOcean",
                "cloudflare": "Cloudflare", "render": "Render",
                "self-host": "Self-Hosted", "local": "Local Development",
                "no deployment": "No Deployment", "none": "No Deployment",
                "skip": "No Deployment",
            }
            for pattern, target in deploy_map.items():
                if pattern in lowered:
                    updates["deployment"] = target
                    break

        return updates

    def infer(self, state: dict) -> dict:
        """Return a dict of inferred values based on known state. Only infer for unknown fields."""
        inferred: dict = {}
        ptype = state.get("project_type")
        purpose = state.get("purpose")

        for rule in _INFERENCES:
            match = False
            if "if_type" in rule and ptype == rule["if_type"]:
                match = True
            if "if_purpose" in rule and purpose == rule["if_purpose"]:
                match = True

            if match:
                for field, value in rule["infer"].items():
                    current = state.get(field)
                    is_empty = current is None or current == "" or (isinstance(current, list) and len(current) == 0)
                    if is_empty:
                        inferred[field] = value

        # -- Project Name Synthesis --
        # Try to synthesize a name if missing, so it doesn't stay null.
        if not state.get("project_name") and "project_name" not in inferred:
            p_type = state.get("project_type") or inferred.get("project_type")
            p_theme = state.get("theme") or inferred.get("theme")
            p_purpose = state.get("purpose") or inferred.get("purpose")
            
            parts = []
            if p_theme:
                parts.append(p_theme.split(" / ")[0])
            elif p_purpose:
                parts.append(p_purpose.split(" / ")[0])
                
            if p_type:
                parts.append(p_type)
                
            if parts:
                inferred["project_name"] = " ".join(parts)

        return inferred

    def is_approval(self, message: str) -> bool:
        """Check if the message is an approval response."""
        return bool(_APPROVAL_PATTERNS.search(message.strip()))

    def _extract_name(self, text: str) -> str | None:
        """Try to extract a project name from the message."""
        patterns = [
            r"(?:called|named|name it|project name is|project name)\s+[\"']?([A-Za-z0-9][A-Za-z0-9\-\s]{1,40}?)[\"']?(?:\s*[,.]|\s*$)",
            r"(?:build|create|make)\s+(?:a\s+|an\s+|the\s+)?(?:website|app|application|dashboard|platform|portal|system|tool)\s+for\s+(?:a\s+|an\s+|the\s+)?([A-Za-z0-9\s]+?)(?:\s*[,.]|\s*$)",
            r"(?:build|create|make)\s+(?:a\s+|an\s+|the\s+)?(.+?)(?:\s+(?:website|app|application|dashboard|platform|tool|system|page|site|portal))",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip(" .")
                # Filter out generic words
                skip = {"a", "an", "the", "my", "our", "me", "i", "just", "simple", "basic", "cool", "fun", "nice", "good", "new"}
                if candidate.lower() not in skip and len(candidate) >= 2:
                    return candidate.title()
        return None


# ── Singleton ─────────────────────────────────────────────────────────────

requirement_extractor = RequirementExtractor()
