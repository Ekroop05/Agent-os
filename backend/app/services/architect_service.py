"""
Architect Service — the orchestrator.

Flow:
  User message
    → Requirement Extractor (rule-based, instant)
    → Inference Engine (rule-based, instant)
    → Project State Manager (update & recalculate)
    → Planner Agent (LLM, only when needed, receives state context)
    → Response with live state
"""

from __future__ import annotations

import json
import re
import uuid

from fastapi import HTTPException

from app.services.spec_engine import spec_engine
from app.services.project_name_generator import generate_name, sanitize_name

from app.extractors.requirement_extractor import requirement_extractor
from app.schemas import ArchitectChatResponse
from app.services.llm_service import generate_response
from app.state.project_state import project_state_manager, MAX_CLARIFICATION_ROUNDS

ARCHITECT_MODEL = "qwen3:14b"


class ArchitectService:

    def classify_intent(self, message: str) -> str:
        msg = message.lower().strip()
        project_verbs = ["build", "create", "generate", "develop", "modify", "edit", "improve", "make", "design", "scaffold", "update", "change", "add"]
        if any(v in msg for v in project_verbs):
            if any(v in msg for v in ["modify", "edit", "improve", "update", "change", "add"]):
                return "Project Modification"
            return "Project Creation"

        if msg in {"hi", "hello", "hey", "good morning", "good afternoon", "good evening", "how are you?", "how are you", "yo", "sup", "greetings"} or (len(msg) < 15 and any(msg.startswith(g) for g in ["hi", "hello", "hey"])):
            return "Greeting"
        if msg in {"help", "help me", "how does this work", "how do i start", "what can you do", "what can you do?"}:
            return "Help"
        if msg in {"thanks", "thank you", "cool", "awesome", "nice", "ok", "okay", "got it"}:
            return "General Conversation"
        if msg.endswith("?") or any(msg.startswith(q) for q in ["what is", "who are", "can you", "do you", "why"]):
            return "Question"

        if len(msg) > 25:
            return "Project Creation"
        return "Unknown"

    # ── Main chat entry point ─────────────────────────────────────────────

    def chat(self, message: str, conversation_id: str | None = None) -> ArchitectChatResponse:
        intent = self.classify_intent(message)
        existing_state = project_state_manager.get(conversation_id) if conversation_id else None
        has_active_project = existing_state and (existing_state.get("requirements_progress", 0) > 0 or existing_state.get("project_name"))

        if intent in {"Greeting", "General Conversation", "Help", "Question", "Unknown"} and not has_active_project:
            cid = conversation_id or str(uuid.uuid4())
            if intent == "Greeting":
                reply = "Hello! I'm the Architect Agent.\n\nI can help you plan and build websites, applications and software projects.\n\nWhat would you like to create today?"
            elif intent == "Help":
                reply = "I'm the Architect Agent. To get started, describe what you want to build (e.g., 'Build me a SaaS dashboard' or 'Create a portfolio website'). I'll extract your requirements and generate a plan!"
            else:
                reply = "I'm the Architect Agent, your technical co-founder. Tell me what application, website, or software project you'd like to create, and let's get started!"
            
            return ArchitectChatResponse(
                conversation_id=cid,
                reply=reply,
                requirements_complete=False,
                approval_required=False,
                current_phase="Discovering Requirements",
                requirements_progress=0,
                confidence_score=0,
            )

        if intent in {"Greeting", "General Conversation"} and has_active_project:
            reply = "Hello! I'm ready to continue with your project. You can review the state panel on the right and click Approve Project, or tell me what features to add or modify."
            project_state_manager.add_message(existing_state, "user", message)
            project_state_manager.add_message(existing_state, "assistant", reply)
            return self._build_response(existing_state, reply)

        state = project_state_manager.get_or_create(conversation_id)
        project_state_manager.add_message(state, "user", message)

        # Step 1: Extract requirements (rule-based, instant)
        extracted = requirement_extractor.extract(message, state)
        project_state_manager.update_many(state, extracted)

        # Step 2: Infer missing fields from what we know
        inferred = requirement_extractor.infer(state)
        project_state_manager.update_many(state, inferred)

        # Step 3: Decide what to do
        project_state_manager.recalculate(state)
        
        if state["current_phase"] == "PROJECT_CREATION":
            reply = "This project has already been approved. Start a new conversation to plan another project."
            
        elif state["current_phase"] == "AWAITING_APPROVAL":
            if requirement_extractor.is_approval(message):
                return self._do_approve_inline(state)
            else:
                reply = self._awaiting_reply(state)
                
        elif state["current_phase"] == "ARCHITECTURE_GENERATION":
            if not state.get("architecture_generated"):
                architecture = self._generate_architecture(state)
                state["architecture"] = architecture
                state["project_name"] = architecture.get("project_name") or state["project_name"] or "Untitled Project"
                state["architecture_generated"] = True
                # Sprint 4: Generate project specification
                state["spec"] = spec_engine.generate_spec(state)
                state["project_name"] = state["spec"]["project_name"]
                project_state_manager.recalculate(state)
                reply = self._format_architecture_reply(architecture)
            else:
                reply = self._awaiting_reply(state)
                
        else: # REQUIREMENT_DISCOVERY
            project_state_manager.increment_clarification(state)
            project_state_manager.recalculate(state)
            
            never_asked = project_state_manager.unanswered_unasked_fields(state)
            
            if state["current_phase"] == "ARCHITECTURE_GENERATION" or not never_asked:
                if not state.get("requirements_complete"):
                    state["requirements_complete"] = True
                    project_state_manager.recalculate(state)
                
                architecture = self._generate_architecture(state)
                state["architecture"] = architecture
                state["project_name"] = architecture.get("project_name") or state["project_name"] or "Untitled Project"
                state["architecture_generated"] = True
                # Sprint 4: Generate project specification
                state["spec"] = spec_engine.generate_spec(state)
                state["project_name"] = state["spec"]["project_name"]
                project_state_manager.recalculate(state)
                reply = self._format_architecture_reply(architecture)
            else:
                reply = self._conversational_reply(state)

        project_state_manager.add_message(state, "assistant", reply)
        return self._build_response(state, reply)

    # ── Approve ───────────────────────────────────────────────────────────

    def approve(self, conversation_id: str) -> dict:
        state = project_state_manager.get(conversation_id)
        if not state:
            raise HTTPException(status_code=404, detail="Conversation not found")
        with open("logs/approve_project_trace.log", "a") as f:
            f.write("CONVERSATION_FOUND\n")
            
        if not state["architecture_generated"]:
            raise HTTPException(status_code=400, detail="Architecture has not been generated yet")
        if state["approved"]:
            raise HTTPException(status_code=400, detail="Project has already been approved")
            
        with open("logs/approve_project_trace.log", "a") as f:
            f.write("STATE_VALIDATED\n")
            
        state["approved"] = True
        project_state_manager.recalculate(state)
        return state

    def _do_approve_inline(self, state: dict) -> ArchitectChatResponse:
        """User said 'yes' / 'approve' in chat — approve inline."""
        state["approved"] = True
        project_state_manager.recalculate(state)
        name = state.get("project_name") or "the project"
        reply = (
            f"Approved! I'm setting up the workspace for **{name}** now.\n\n"
            f"Head over to the Workspaces and Tasks pages to see everything. Let's build something great."
        )
        project_state_manager.add_message(state, "assistant", reply)
        return self._build_response(state, reply)

    # ── Conversational reply (LLM) ────────────────────────────────────────

    def _conversational_reply(self, state: dict) -> str:
        never_asked = project_state_manager.unanswered_unasked_fields(state)

        # Pick at most 2 fields to ask about — ONLY from never-asked fields
        ask_about = never_asked[:2]

        # Mark them as asked so we don't ask again
        for field in ask_about:
            project_state_manager.mark_question_asked(state, field)

        # Build prompt with full state context
        prompt = self._build_prompt(state, ask_about)

        try:
            reply = generate_response(ARCHITECT_MODEL, prompt).strip()
            # Strip <think>...</think> tags
            reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()
            if reply and len(reply) > 10:
                return reply
        except Exception:
            pass

        # Fallback: rule-based response
        return self._fallback_reply(state, ask_about)

    def _build_prompt(self, state: dict, ask_about: list[str]) -> str:
        state_summary = project_state_manager.state_summary_for_llm(state)
        recent = project_state_manager.recent_messages(state, 8)
        transcript = "\n".join(f"{m['role']}: {m['content']}" for m in recent)

        field_labels = {
            "project_name": "what the project should be called",
            "project_type": "what kind of application this is",
            "theme": "the visual theme or domain",
            "purpose": "the main purpose or goal",
            "target_users": "who will use this",
            "core_features": "what key features are needed",
            "frontend": "preferred frontend technology",
            "backend": "preferred backend technology",
            "database": "what database to use",
            "authentication": "whether users need accounts/login",
            "deployment": "where this will be deployed",
        }
        questions_text = ""
        if ask_about:
            items = [field_labels.get(f, f.replace("_", " ")) for f in ask_about]
            questions_text = f"Ask about: {', '.join(items)}"
        else:
            questions_text = "You have enough information. Say so and hint that you're ready to design the architecture."

        return f"""You are the Lead Architect of Agent OS — a senior technical leader with the mind of a startup CTO.

PERSONALITY:
- Professional, intelligent, curious, and collaborative
- Technically confident and slightly visionary
- Friendly but not overly casual — like a CTO planning a real product
- You are NOT a survey bot, form wizard, or customer support agent

STRICT RULES:
- NEVER repeat a question about something already known
- NEVER list 3+ questions — ask at most 1-2 naturally
- Acknowledge what the user said and show genuine engagement
- If something can be inferred, state your assumption instead of asking
- Keep your reply under 120 words
- Do NOT use XML tags like <think> in your response

{state_summary}

{questions_text}

Recent conversation:
{transcript}

Respond naturally as the Architect."""

    def _fallback_reply(self, state: dict, ask_about: list[str]) -> str:
        """Rule-based fallback when LLM is unavailable."""
        parts = []

        # Summarize what we know
        known_items = []
        if state.get("project_type"):
            known_items.append(f"a {state['project_type']}")
        if state.get("theme"):
            known_items.append(f"with a {state['theme']} theme")
        if state.get("purpose"):
            known_items.append(f"for {state['purpose']}")
        if known_items:
            parts.append(f"Great — so we're building {' '.join(known_items)}.")
        else:
            parts.append("Interesting idea! Let me understand it better.")

        # Ask about missing fields
        field_questions = {
            "project_name": "What should we call this project?",
            "project_type": "What kind of application is this — a website, web app, dashboard?",
            "theme": "Is there a specific theme or domain for this project?",
            "purpose": "What's the main purpose — entertainment, business, education?",
            "target_users": "Who's the primary audience — general visitors, specific professionals?",
            "core_features": "What should users be able to do in the first version?",
            "frontend": "Any frontend preference? React, Vue, plain HTML?",
            "backend": "Do you need a backend, or is this purely client-side?",
            "database": "Will this need a database?",
            "authentication": "Should users be able to create accounts and log in?",
            "deployment": "Where do you want to deploy this?",
        }
        if ask_about:
            parts.append("")
            for field in ask_about[:2]:
                q = field_questions.get(field, f"Tell me about the {field.replace('_', ' ')}.")
                parts.append(f"• {q}")

        return "\n".join(parts)

    # ── Awaiting approval reply ───────────────────────────────────────────

    def _awaiting_reply(self, state: dict) -> str:
        name = state.get("project_name") or "the project"
        return (
            f"The architecture for **{name}** is ready for your review.\n\n"
            f"Check the proposal in the Project State panel.\n\n"
            f"Say **\"approve\"** or click **Approve Project** when you're ready to go."
        )

    # ── Architecture generation ───────────────────────────────────────────

    def _generate_architecture(self, state: dict) -> dict:
        name = state.get("project_name") or "Project"
        state_summary = project_state_manager.state_summary_for_llm(state)

        prompt = f"""You are the Lead Technical Architect. Return ONLY valid JSON, no markdown fences, no explanation.
Design the architecture for: {name}

{state_summary}

JSON keys:
- project_name (string)
- architecture (string: 2-3 sentence overall architecture description)
- tech_stack (array of strings)
- major_components (array of strings, 4-6 components)
- development_plan (array of strings, 3-5 phases)
- task_breakdown (array of objects with: title, description, priority)

Return 5-8 tasks in task_breakdown covering the full build.
Do NOT wrap the JSON in markdown code fences."""

        try:
            raw = generate_response(ARCHITECT_MODEL, prompt)
            # Strip think tags
            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            parsed = json.loads(self._extract_json(raw))
            return self._normalize(parsed, state)
        except Exception:
            return self._fallback_architecture(state)

    def _extract_json(self, raw: str) -> str:
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "")
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("No JSON found")
        return cleaned[start:end + 1]

    def _normalize(self, arch: dict, state: dict) -> dict:
        fallback = self._fallback_architecture(state)
        merged = {**fallback, **{k: v for k, v in arch.items() if v}}
        if not isinstance(merged.get("task_breakdown"), list):
            merged["task_breakdown"] = fallback["task_breakdown"]
        return merged

    def _fallback_architecture(self, state: dict) -> dict:
        # Sprint 4: Use project name generator instead of generic names
        name = state.get("project_name")
        ptype = state.get("project_type") or "Web Application"
        if not name or sanitize_name(name) == "":
            name = generate_name(
                theme=state.get("theme"),
                project_type=ptype,
                purpose=state.get("purpose"),
            )
        features = state.get("core_features") or []
        frontend = state.get("frontend") or "React + Vite"
        backend = state.get("backend")
        database = state.get("database")

        # Sprint 4: Architecture consistency — respect backend/database=False
        has_backend = backend and backend is not False
        has_database = database and database is not False

        tech = [frontend] if frontend and frontend is not False else ["HTML/CSS/JS"]
        if has_backend:
            tech.append(backend)
        if has_database:
            tech.append(database)

        # Sprint 4: Adjust architecture description and components based on actual requirements
        if has_backend:
            arch_desc = f"A modular {ptype.lower()} with a responsive frontend, API layer, and data persistence."
            components = [
                "Frontend Application Shell",
                "API & Service Layer",
                "Data Model & Storage",
                "User Interface Components",
                "Activity & Audit Trail",
            ]
            dev_plan = [
                "Define scope and core workflows",
                "Design data model and API contracts",
                "Build frontend shell and core pages",
                "Implement backend services and integrations",
                "Testing, polish, and deployment",
            ]
        else:
            arch_desc = f"A client-side {ptype.lower()} with a rich, responsive frontend and static assets."
            components = [
                "Frontend Application Shell",
                "User Interface Components",
                "Page Router & Navigation",
                "Theme & Styling System",
                "Static Asset Management",
            ]
            dev_plan = [
                "Define scope and core workflows",
                "Build frontend shell and core pages",
                "Implement UI components and features",
                "Testing, polish, and deployment",
            ]

        # Sprint 4: Build task breakdown — no backend tasks when backend=False
        tasks = [
            {"title": "Define product scope", "description": f"Document goals, users, and constraints for {name}.", "priority": "High"},
            {"title": "Design system architecture", "description": "Create the service, data, and interface architecture.", "priority": "High"},
            {"title": "Build frontend shell", "description": "Implement layout, navigation, and core pages.", "priority": "High"},
        ]
        if has_backend:
            tasks.append({"title": "Build backend API", "description": "Implement REST endpoints and business logic.", "priority": "High"})
        tasks.append(
            {"title": f"Implement {features[0] if features else 'core features'}", "description": "Build the primary user-facing features.", "priority": "High"}
        )
        if has_backend:
            tasks.append({"title": "Integration testing", "description": "Connect frontend to backend and test all workflows.", "priority": "Medium"})
        tasks.append(
            {"title": "Polish and deploy", "description": "Final UI polish, performance optimization, deployment.", "priority": "Medium"}
        )

        return {
            "project_name": name,
            "architecture": arch_desc,
            "tech_stack": tech,
            "major_components": components,
            "development_plan": dev_plan,
            "task_breakdown": tasks,
        }

    def _format_architecture_reply(self, arch: dict) -> str:
        name = arch.get("project_name", "the project")
        desc = arch.get("architecture", "")
        tech = arch.get("tech_stack", [])[:5]
        components = arch.get("major_components", [])[:5]
        tasks = arch.get("task_breakdown", [])

        return "\n".join([
            f"I've designed the architecture for **{name}**.\n",
            f"{desc}\n",
            f"**Tech Stack:** {', '.join(str(t) for t in tech)}\n",
            f"**Core Components:** {', '.join(str(c) for c in components)}\n",
            f"I've broken this into **{len(tasks)} planning tasks**.\n",
            "Review the proposal in the Project State panel. When you're happy, say **\"approve\"** or click **Approve Project**.",
        ])

    # ── Response builder ──────────────────────────────────────────────────

    def _build_response(self, state: dict, reply: str) -> ArchitectChatResponse:
        return ArchitectChatResponse(
            conversation_id=state["conversation_id"],
            reply=reply,
            requirements_complete=state["requirements_complete"],
            approval_required=state["architecture_generated"] and not state["approved"],
            project_name=state.get("project_name"),
            architecture=state.get("architecture"),
            approved=state["approved"],
            current_phase=state["current_phase"],
            requirements_progress=state["requirements_progress"],
            confidence_score=state["confidence_score"],
        )


# ── Singleton ─────────────────────────────────────────────────────────────

architect_service = ArchitectService()
