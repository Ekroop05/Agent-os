import json
import re
import uuid

from fastapi import HTTPException

from app.schemas import ArchitectChatResponse
from app.services.llm_service import generate_response

ARCHITECT_MODEL = "qwen3:14b"

REQUIREMENT_FIELDS = {
    "project_type": ("app", "site", "website", "dashboard", "api", "tool", "game", "platform", "system", "service", "portal", "marketplace", "blog", "cms", "crm", "erp"),
    "users": ("user", "customer", "admin", "team", "student", "developer", "operator", "visitor", "member", "player", "viewer", "client", "employee", "manager"),
    "features": ("feature", "login", "auth", "chat", "upload", "payment", "search", "dashboard", "report", "notification", "profile", "gallery", "list", "detail", "page", "form", "chart", "map", "filter", "sort", "browse", "create", "edit", "delete", "responsive"),
    "data": ("data", "database", "store", "file", "record", "api", "integration", "storage", "cloud", "local", "cache", "session", "json", "sql", "nosql", "image", "video", "content"),
    "constraints": ("deadline", "budget", "stack", "must", "mobile", "desktop", "security", "privacy", "scale", "react", "vue", "angular", "node", "python", "django", "flask", "fastapi", "typescript", "performance", "accessibility"),
}

PHASE_DISCOVERING = "Discovering Requirements"
PHASE_ANALYZING = "Analyzing User Goals"
PHASE_DEFINING = "Defining Features"
PHASE_DESIGNING = "Designing Architecture"
PHASE_AWAITING = "Awaiting Approval"
PHASE_CREATING_WS = "Creating Workspace"
PHASE_GENERATING = "Generating Tasks"
PHASE_READY = "Project Ready"


class PlannerAgent:
    def __init__(self):
        self.conversations: dict[str, dict] = {}

    def chat(self, message: str, conversation_id: str | None = None) -> ArchitectChatResponse:
        conversation = self._conversation(conversation_id)
        conversation["messages"].append({"role": "user", "content": message})
        self._extract_requirements(conversation, message)
        self._update_phase(conversation)

        if conversation["approved"]:
            reply = "This project has already been approved and is being built. Start a new conversation if you'd like to plan another project."
        elif conversation["architecture_generated"]:
            reply = self._awaiting_reply(conversation)
        elif self._requirements_complete(conversation):
            architecture = self._generate_architecture(conversation)
            conversation["architecture"] = architecture
            conversation["project_name"] = architecture.get("project_name") or conversation["project_name"]
            conversation["architecture_generated"] = True
            conversation["current_phase"] = PHASE_AWAITING
            conversation["confidence_score"] = 90
            reply = self._format_architecture_reply(architecture)
        else:
            reply = self._question_reply(conversation)

        conversation["messages"].append({"role": "assistant", "content": reply})
        return self._response(conversation, reply)

    def get(self, conversation_id: str) -> dict:
        conversation = self.conversations.get(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation

    def approve(self, conversation_id: str) -> dict:
        conversation = self.get(conversation_id)
        if not conversation["architecture_generated"]:
            raise HTTPException(status_code=400, detail="Architecture has not been generated yet")
        if conversation["approved"]:
            raise HTTPException(status_code=400, detail="Project has already been approved")
        conversation["approved"] = True
        conversation["current_phase"] = PHASE_READY
        conversation["confidence_score"] = 100
        return conversation

    def _conversation(self, conversation_id: str | None) -> dict:
        if conversation_id and conversation_id in self.conversations:
            return self.conversations[conversation_id]

        new_id = conversation_id or str(uuid.uuid4())
        self.conversations[new_id] = {
            "conversation_id": new_id,
            "messages": [],
            "extracted_requirements": {},
            "project_name": None,
            "architecture": None,
            "architecture_generated": False,
            "approved": False,
            "current_phase": PHASE_DISCOVERING,
            "requirements_progress": 0,
            "confidence_score": 5,
        }
        return self.conversations[new_id]

    # ── Requirement extraction ───────────────────────────────────────────

    def _extract_requirements(self, conversation: dict, message: str) -> None:
        text = message.strip()
        if not text:
            return
        requirements = conversation["extracted_requirements"]

        # Fast regex for project name
        if not conversation["project_name"]:
            name_match = re.search(
                r"(?:called|named|name it|project name|project|app|build)\s+([a-z0-9][a-z0-9\-\s]{1,40})",
                text, re.I,
            )
            if name_match:
                candidate = name_match.group(1).strip(" .")
                if len(candidate) >= 2 and candidate.lower() not in ("a", "an", "the", "my", "our", "is", "it"):
                    conversation["project_name"] = candidate

        # LLM-powered extraction
        prompt = f"""You are a strict requirement extractor. Analyze the user message and extract project requirements.
Fields: {', '.join(REQUIREMENT_FIELDS.keys())}, project_name
Current requirements: {json.dumps(requirements)}
Current project name: {conversation["project_name"] or "not set"}

User message: "{text}"

Return ONLY valid JSON with fields you found. Use short descriptions as values. 
If nothing relevant is found, return {{}}.
Do NOT include fields that are not mentioned or implied by the message.
Do NOT wrap the JSON in markdown code fences."""
        try:
            raw = generate_response(ARCHITECT_MODEL, prompt)
            parsed = json.loads(self._json_text(raw))
            for k, v in parsed.items():
                if k == "project_name" and v and not conversation["project_name"]:
                    val = str(v).strip(" .")
                    if len(val) >= 2:
                        conversation["project_name"] = val
                elif k in REQUIREMENT_FIELDS and v:
                    requirements[k] = str(v)
        except Exception:
            # Fallback to keyword matching
            lowered = text.lower()
            for field, keywords in REQUIREMENT_FIELDS.items():
                if field not in requirements and any(kw in lowered for kw in keywords):
                    requirements[field] = text

        # Update progress
        self._update_progress(conversation)

    def _update_progress(self, conversation: dict) -> None:
        requirements = conversation["extracted_requirements"]
        total = len(REQUIREMENT_FIELDS)
        covered = sum(1 for f in REQUIREMENT_FIELDS if f in requirements)
        has_name = 1 if conversation["project_name"] else 0
        raw = int(((covered + has_name) / (total + 1)) * 100)
        conversation["requirements_progress"] = min(raw, 100)

        # Confidence is based on progress + message count
        msg_count = len([m for m in conversation["messages"] if m["role"] == "user"])
        base_confidence = raw
        if msg_count >= 2:
            base_confidence = min(base_confidence + 10, 95)
        if conversation["architecture_generated"]:
            base_confidence = 90
        if conversation["approved"]:
            base_confidence = 100
        conversation["confidence_score"] = base_confidence

    # ── Phase management ─────────────────────────────────────────────────

    def _update_phase(self, conversation: dict) -> None:
        if conversation["approved"]:
            conversation["current_phase"] = PHASE_READY
            return
        if conversation["architecture_generated"]:
            conversation["current_phase"] = PHASE_AWAITING
            return

        progress = conversation["requirements_progress"]
        covered = sum(1 for f in REQUIREMENT_FIELDS if f in conversation["extracted_requirements"])

        if progress >= 80:
            conversation["current_phase"] = PHASE_DESIGNING
        elif covered >= 3:
            conversation["current_phase"] = PHASE_DEFINING
        elif covered >= 1:
            conversation["current_phase"] = PHASE_ANALYZING
        else:
            conversation["current_phase"] = PHASE_DISCOVERING

    def _requirements_complete(self, conversation: dict) -> bool:
        requirements = conversation["extracted_requirements"]
        covered = [field for field in REQUIREMENT_FIELDS if field in requirements]
        return bool(conversation["project_name"]) and len(covered) >= 4

    # ── Conversation replies ─────────────────────────────────────────────

    def _question_reply(self, conversation: dict) -> str:
        missing = [f for f in REQUIREMENT_FIELDS if f not in conversation["extracted_requirements"]]
        prompt = self._prompt(conversation, missing)
        try:
            reply = generate_response(ARCHITECT_MODEL, prompt).strip()
            # Strip <think>...</think> tags that some models produce
            reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()
            if reply:
                return reply
        except Exception:
            pass

        # Intelligent fallback
        return self._fallback_question_reply(conversation, missing)

    def _awaiting_reply(self, conversation: dict) -> str:
        arch = conversation["architecture"]
        name = arch.get("project_name", "the project") if arch else "the project"
        return (
            f"The architecture for **{name}** is ready for your review. "
            f"Take a look at the proposal in the Project State panel on the right.\n\n"
            f"When you're satisfied, hit **Approve Project** and I'll create the workspace and generate the planning tasks."
        )

    def _fallback_question_reply(self, conversation: dict, missing: list[str]) -> str:
        requirements = conversation["extracted_requirements"]
        parts = []

        if requirements:
            covered = ", ".join(f.replace("_", " ") for f in requirements)
            parts.append(f"Here's what I've gathered so far: {covered}.")
        else:
            parts.append("I'd love to hear more about what you're building.")

        questions = {
            "project_type": "What kind of application are you envisioning — a web app, mobile app, API, dashboard?",
            "users": "Who will be using this? End consumers, internal teams, developers?",
            "features": "What are the key things a user should be able to do in the first version?",
            "data": "What data does the system need to manage — user content, external APIs, files?",
            "constraints": "Any technical preferences or constraints? Particular frameworks, platforms, or deployment targets?",
        }
        next_qs = [questions[f] for f in missing[:2] if f in questions]
        if next_qs:
            parts.append("\nA couple of things I'd like to understand:")
            for q in next_qs:
                parts.append(f"• {q}")

        return "\n".join(parts)

    def _prompt(self, conversation: dict, missing: list[str]) -> str:
        transcript = "\n".join(f"{m['role']}: {m['content']}" for m in conversation["messages"][-10:])
        requirements = conversation["extracted_requirements"]
        project_name = conversation["project_name"] or "not yet named"
        progress = conversation["requirements_progress"]

        return f"""You are the Lead Architect of Agent OS — a senior technical leader with the mind of a startup CTO.

PERSONALITY:
- Professional, intelligent, curious, and collaborative
- Technically confident and slightly visionary
- Friendly but not overly casual
- You think like a Senior Software Architect / startup CTO / Technical Product Manager
- You are NOT a survey bot, form wizard, or customer support agent

CONVERSATION STYLE:
- Acknowledge what the user said and show genuine engagement with the idea
- Summarize your understanding naturally, not as a bulleted checklist
- Ask at most 1-2 thoughtful clarifying questions — never a numbered list of 5+ questions
- If the user provides a rich description, infer reasonable defaults and only ask about genuine ambiguity
- NEVER repeat a question that has already been answered
- Use a tone that feels like collaborating with a CTO planning a real product

CONTEXT:
- Project name: {project_name}
- Requirements progress: {progress}%
- Collected requirements: {json.dumps(requirements)}
- Still missing: {", ".join(missing) if missing else "none"}

TRANSCRIPT:
{transcript}

INSTRUCTIONS:
1. Show that you understood and absorbed the user's latest message
2. Briefly summarize your current understanding of the project (naturally, not as a form)
3. If there are missing fields, ask 1-2 smart questions that a CTO would ask
4. If almost everything is covered, say so and hint that you're almost ready to design the architecture
5. Keep your reply concise — under 150 words
6. Do NOT use any XML-like tags such as <think> in your response"""

    # ── Architecture generation ──────────────────────────────────────────

    def _generate_architecture(self, conversation: dict) -> dict:
        requirements = conversation["extracted_requirements"]
        project_name = conversation["project_name"] or "Project"
        prompt = f"""You are the Lead Technical Architect. Return ONLY valid JSON, no markdown fences.
Create a detailed architecture proposal for: {project_name}
Requirements: {json.dumps(requirements)}

JSON keys:
- project_name (string)
- architecture (string: 2-3 sentence description of the overall architecture)
- tech_stack (array of strings)
- major_components (array of strings, 4-6 components)
- development_plan (array of strings, 3-5 phases)
- task_breakdown (array of objects with: title, description, priority)

Return 5-8 tasks in task_breakdown covering the full build.
Do NOT wrap the JSON in markdown code fences."""
        try:
            raw = generate_response(ARCHITECT_MODEL, prompt)
            parsed = json.loads(self._json_text(raw))
            return self._normalize_architecture(parsed, conversation)
        except Exception:
            return self._fallback_architecture(conversation)

    def _json_text(self, raw: str) -> str:
        # Strip markdown code fences if present
        cleaned = re.sub(r"```(?:json)?\s*", "", raw)
        cleaned = cleaned.replace("```", "")
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("No JSON object found")
        return cleaned[start : end + 1]

    def _normalize_architecture(self, architecture: dict, conversation: dict) -> dict:
        fallback = self._fallback_architecture(conversation)
        normalized = {**fallback, **{k: v for k, v in architecture.items() if v}}
        if not isinstance(normalized.get("task_breakdown"), list):
            normalized["task_breakdown"] = fallback["task_breakdown"]
        return normalized

    def _fallback_architecture(self, conversation: dict) -> dict:
        project_name = conversation["project_name"] or "Generated Project"
        requirements = conversation["extracted_requirements"]
        return {
            "project_name": project_name,
            "architecture": "A modular application with a user-facing client, backend API, persistence layer, and operational event logging.",
            "tech_stack": ["React + Vite", "FastAPI", "SQLite or PostgreSQL", "Local LLM-assisted planning"],
            "major_components": [
                "User experience shell",
                "API and service layer",
                "Data model and storage",
                "Authentication and permissions",
                "Activity and audit trail",
            ],
            "development_plan": [
                "Confirm scope and first-version workflows",
                "Design data model and API contracts",
                "Build the primary interface and backend services",
                "Add validation, activity logging, and review checkpoints",
            ],
            "task_breakdown": [
                {"title": "Define product scope", "description": requirements.get("summary", "Document goals, users, and constraints."), "priority": "High"},
                {"title": "Design system architecture", "description": "Create the service, data, and interface architecture for the approved project.", "priority": "High"},
                {"title": "Build frontend shell", "description": "Implement the main application layout, navigation, and core pages.", "priority": "High"},
                {"title": "Build backend API", "description": "Implement the REST API endpoints, data models, and business logic.", "priority": "High"},
                {"title": "Integration and testing", "description": "Connect frontend to backend, add validation, and test all workflows.", "priority": "Medium"},
                {"title": "Polish and deploy", "description": "Final UI polish, performance optimization, and deployment setup.", "priority": "Medium"},
            ],
        }

    def _format_architecture_reply(self, architecture: dict) -> str:
        name = architecture.get("project_name", "the project")
        arch_desc = architecture.get("architecture", "")
        components = architecture.get("major_components", [])[:5]
        tech = architecture.get("tech_stack", [])[:5]
        tasks = architecture.get("task_breakdown", [])

        parts = [
            f"I've designed the architecture for **{name}**.\n",
            f"{arch_desc}\n",
            f"**Tech Stack:** {', '.join(tech)}\n",
            f"**Core Components:** {', '.join(components)}\n",
            f"I've broken this down into **{len(tasks)} planning tasks** that will guide the build.\n",
            "Take a look at the full proposal in the Project State panel. When you're happy with it, hit **Approve Project** to kick things off.",
        ]
        return "\n".join(parts)

    # ── Response builder ─────────────────────────────────────────────────

    def _response(self, conversation: dict, reply: str) -> ArchitectChatResponse:
        return ArchitectChatResponse(
            conversation_id=conversation["conversation_id"],
            reply=reply,
            requirements_complete=self._requirements_complete(conversation),
            approval_required=conversation["architecture_generated"] and not conversation["approved"],
            project_name=conversation["project_name"],
            architecture=conversation["architecture"],
            approved=conversation["approved"],
            current_phase=conversation["current_phase"],
            requirements_progress=conversation["requirements_progress"],
            confidence_score=conversation["confidence_score"],
        )


planner_agent = PlannerAgent()
