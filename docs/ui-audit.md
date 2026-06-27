# UI Comprehensive Audit — Agent OS v2

This document audits all eight primary page views in the Agent OS React frontend (`frontend/src/pages/`), analyzing their purpose, data sources, functional features, defects, navigation flows, design consistency, and future opportunities.

---

## 1. Page-by-Page Analysis

| Page | Purpose | Data Source | Current Features | Broken Features | Navigation | Future Opportunities |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Dashboard** (`Dashboard.jsx`) | System command center & quick launch | REST `/api/workspaces`, WebSocket `/ws/system` | Active Build Overview card, Quick Action launchers, Recent Workspaces grid | None (Fixed in Stabilization Sprint) | 1-click navigate to `/architect` or `/workspaces` | Customizable dashboard layouts & project bookmarking |
| **Architect** (`Architect.jsx`) | Conversational AI requirement gathering | REST `/api/architect/chat`, `architectStore.js` | Chat composer, intent pre-filtering, auto-focus input, requirement progress bar | None | Smooth transitions to Workspace building upon approval | Rich markdown previewing & interactive voice input |
| **Workspaces** (`Workspaces.jsx`) | Live inspection of build execution & file generation | WebSocket `/ws/workspaces` & `/ws/build` | Auto-selection of active build, File Explorer, Task Graph, Build Timeline, Failure Diagnostics | Minor CSS scrollbar overlap on deeply nested file trees in File Explorer | Tabs switch between Code, Tasks, Timeline, and Diagnostics | Split-screen live preview diffing alongside code tree |
| **Tasks** (`Tasks.jsx`) | Master inventory of all development tasks | REST `/api/tasks`, WebSocket `/ws/task` | Status filter tabs (`Pending`, `Running`, `Completed`, `Failed`), search bar | Filter state resets when navigating away and returning | Clicking task routes to Workspace view | Drag-and-drop Kanban board view for task reprioritization |
| **Agents** (`Agents.jsx`) | Status overview of AI personas | WebSocket `/ws/agents` | Persona cards (Architect, Builder, Security), current status badges, model label | Static model display does not update if changed in Settings | None | Agent execution logs & fine-tuning configuration modal |
| **Activity** (`Activity.jsx`) | Real-time system feed | WebSocket `/ws/activity` | Scrolling terminal log feed, timestamp tagging | High volume build logs can cause DOM slowdown after 1,000+ lines | None | Export log to `.txt`/`.json` & regex filter bar |
| **Sandbox** (`Sandbox.jsx`) | Runtime preview & testing | REST `/api/runtime`, WebSocket `/ws/build` | Container control panel (`Start`, `Stop`), embedded iframe preview URL | Iframe fails if generated server fails to bind port 0.0.0.0 | None | Console network inspector integrated into sandbox panel |
| **Settings** (`Settings.jsx`) | System configuration | LocalStorage / REST config | Model selector dropdown (`Gemini 3.1 Pro`), API key input, theme toggle | Model selection does not dynamically reload active backend LLM singleton | None | Multi-provider model configuration (OpenAI, Anthropic, Ollama) |

---

## 2. Identified Duplicated & Inconsistent UI

### Duplicated UI
- **Status Badges**: `StatusPill.jsx` and `Badge.jsx` perform nearly identical styling functions across different pages. They should be consolidated into a single unified `StatusBadge` component.
- **Progress Meters**: `ProgressBar.jsx` and custom CSS progress fills inside `SystemMonitor.jsx` duplicate animation keyframes and color logic.

### Inconsistent UI
- **Typography**: While most pages use CSS variables (`--text-sm`, `--font-mono`), older widgets in `Sandbox.jsx` use hardcoded px font sizes.
- **Spacing Tokens**: Card margins alternate between `16px` (`--space-16`) and `12px` (`--space-12`) across different tab views in `Workspaces.jsx`.

---

## 3. Missing UX & Improvements

1. **Global Search / Command Palette (`Ctrl+K`)**: Users lack a rapid keyboard shortcut to jump between specific workspaces, search files, or trigger build actions from anywhere.
2. **Interactive Notification Toast Center**: While background builds run, users only see a header banner. A toast system alerting on specific task completions or build failures would improve multi-tasking.
3. **Optimistic UI Updates**: Clicking "Approve Architecture" should immediately show skeleton loading states rather than waiting for backend WebSocket confirmation envelopes.
