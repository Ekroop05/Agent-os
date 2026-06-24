import { useEffect, useMemo, useState } from "react";
import ErrorBoundary from "./components/ErrorBoundary";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import AgentStatusBar from "./components/AgentStatusBar";
import Activity from "./pages/Activity";
import Agents from "./pages/Agents";
import Architect from "./pages/Architect";
import Dashboard from "./pages/Dashboard";
import Sandbox from "./pages/Sandbox";
import Settings from "./pages/Settings";
import Tasks from "./pages/Tasks";
import Workspaces from "./pages/Workspaces";
import { api } from "./services/api";
import { connectChannel, setOnReconnect } from "./services/websocket";
import "./App-v2.css";

const pages = {
  "/": Dashboard,
  "/architect": Architect,
  "/agents": Agents,
  "/workspaces": Workspaces,
  "/tasks": Tasks,
  "/activity": Activity,
  "/sandbox": Sandbox,
  "/settings": Settings,
};

function getPath() {
  return window.location.pathname in pages ? window.location.pathname : "/";
}

// ── Payload Validators ──────────────────────────────────────────────────
// Reject any object that lacks the minimum fields required to render.

function isValidTask(obj) {
  return obj && typeof obj.id === "string" && typeof obj.status === "string" && typeof obj.title === "string";
}

function isValidAgent(obj) {
  return obj && typeof obj.id === "string" && typeof obj.name === "string" && typeof obj.status === "string";
}

function isValidWorkspace(obj) {
  return obj && typeof obj.id === "string" && typeof obj.name === "string";
}

// ── Envelope Unwrapper ──────────────────────────────────────────────────
// The backend now wraps every WS message in { event_type, source, message, severity, payload }.
// Domain channels (tasks, agents, workspaces) carry full model objects inside payload.
// For backwards compat, if we receive a bare object without event_type, treat it as a legacy payload.

function unwrapEnvelope(raw) {
  if (raw && typeof raw.event_type === "string" && raw.payload !== undefined) {
    return { envelope: raw, payload: raw.payload };
  }
  // Legacy format: the raw message IS the payload
  return { envelope: null, payload: raw };
}

export default function App() {
  const [path, setPath] = useState(getPath);
  const [state, setState] = useState({
    agents: [],
    tasks: [],
    workspaces: [],
    activity: [],
    sandbox: null,
    systemStatus: null,
    buildEvents: [],
    jobs: [],
    timeline: [],
    error: "",
    visibilityMode: "Developer",
  });

  // ── Sprint 4.5: Full state re-sync (used on reconnect + initial load) ──
  async function syncAllState() {
    try {
      const [agents, tasks, workspaces, activity, sandbox, systemStatus, jobs, timeline] = await Promise.all([
        api.getAgents(),
        api.getTasks(),
        api.getWorkspaces(),
        api.getActivity(),
        api.getSandbox(),
        api.getSystemStatus(),
        api.getJobs().catch(() => []),
        api.getTimeline().catch(() => []),
      ]);

      setState((current) => ({
        ...current,
        agents,
        tasks,
        workspaces,
        activity,
        sandbox,
        systemStatus,
        jobs,
        timeline,
        error: "",
      }));
    } catch (error) {
      setState((current) => ({
        ...current,
        error: `Backend unavailable: ${error.message}`,
      }));
    }
  }

  useEffect(() => {
    syncAllState();
  }, []);

  // Sprint 4.5: Register reconnect callback so WebSocket reconnections
  // trigger a full state re-sync from the REST API
  useEffect(() => {
    setOnReconnect(() => {
      console.log("[App] WebSocket reconnected — syncing state");
      syncAllState();
    });
  }, []);

  useEffect(() => {
    const onPopState = () => setPath(getPath());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  // Build-time workspace polling
  useEffect(() => {
    let pollInterval = null;
    const isBuilding = state.workspaces.some(
      (ws) => ws.status === "Building" || ws.status === "Reviewing"
    );

    if (isBuilding) {
      pollInterval = setInterval(() => {
        Promise.all([api.getWorkspaces(), api.getTasks(), api.getJobs().catch(() => [])])
          .then(([workspaces, tasks, jobs]) => {
            setState((current) => ({ ...current, workspaces, tasks, jobs }));
          })
          .catch(() => {});
      }, 5000);
    }

    return () => {
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [state.workspaces]);

  useEffect(() => {
    // ── Activity Channel ────────────────────────────────────────────────
    const activitySocket = connectChannel("activity", (raw) => {
      setState((current) => ({
        ...current,
        activity: [raw, ...current.activity].slice(0, 80),
      }));
    });

    // ── Agents Channel ──────────────────────────────────────────────────
    const agentSocket = connectChannel("agents", (raw) => {
      const { envelope, payload } = unwrapEnvelope(raw);
      if (!isValidAgent(payload)) return;
      setState((current) => ({
        ...current,
        agents: upsertById(current.agents, payload),
      }));
    });

    // ── Tasks Channel ───────────────────────────────────────────────────
    const taskSocket = connectChannel("tasks", (raw) => {
      const { envelope, payload } = unwrapEnvelope(raw);
      if (!isValidTask(payload)) return;
      setState((current) => ({
        ...current,
        tasks: upsertById(current.tasks, payload),
      }));
    });

    // ── Workspaces Channel ──────────────────────────────────────────────
    const workspaceSocket = connectChannel("workspaces", (raw) => {
      const { envelope, payload } = unwrapEnvelope(raw);

      if (payload && payload.deleted) {
        setState((current) => ({
          ...current,
          workspaces: current.workspaces.filter((workspace) => workspace.id !== payload.id),
        }));
        return;
      }

      if (!isValidWorkspace(payload)) return;
      setState((current) => ({
        ...current,
        workspaces: upsertById(current.workspaces, payload),
      }));
    });

    // ── System Channel ──────────────────────────────────────────────────
    const systemSocket = connectChannel("system", (raw) => {
      setState((current) => ({
        ...current,
        systemStatus: raw,
      }));
    });

    // ── Build Channel ───────────────────────────────────────────────────
    const buildSocket = connectChannel("build", (raw) => {
      const { envelope, payload } = unwrapEnvelope(raw);
      setState((current) => ({
        ...current,
        buildEvents: [envelope || raw, ...current.buildEvents].slice(0, 100),
      }));

      // Refresh workspaces and tasks from the API when build progresses
      const wsId = payload?.workspace_id;
      if (wsId) {
        Promise.all([api.getWorkspaces(), api.getTasks()])
          .then(([workspaces, tasks]) => {
            setState((current) => ({ ...current, workspaces, tasks }));
          })
          .catch(() => {});
      }
    });

    // ── Sprint 4.5: Jobs Channel ────────────────────────────────────────
    const jobsSocket = connectChannel("jobs", (raw) => {
      const { envelope, payload } = unwrapEnvelope(raw);
      if (payload && payload.job_id) {
        setState((current) => ({
          ...current,
          jobs: upsertByKey(current.jobs, payload, "job_id"),
        }));
      }
    });

    return () => {
      activitySocket?.close();
      agentSocket?.close();
      taskSocket?.close();
      workspaceSocket?.close();
      systemSocket?.close();
      buildSocket?.close();
      jobsSocket?.close();
    };
  }, []);

  const navigate = (nextPath) => {
    window.history.pushState({}, "", nextPath);
    setPath(nextPath);
  };

  const CurrentPage = pages[path] || Dashboard;
  const title = useMemo(() => {
    const label = path === "/" ? "Dashboard" : path.slice(1);
    return label.charAt(0).toUpperCase() + label.slice(1);
  }, [path]);

  return (
    <div className="app-shell app-shell-v2">
      <Sidebar 
        currentPath={path} 
        onNavigate={navigate} 
        visibilityMode={state.visibilityMode}
        setVisibilityMode={(mode) => setState(s => ({...s, visibilityMode: mode}))}
      />
      <div className="main-shell">
        <Header title={title} systemStatus={state.systemStatus} />
        <main className="page-content">
          {state.error && <div className="system-alert">{state.error}</div>}
          <ErrorBoundary fallbackLabel={title}>
            <CurrentPage data={state} setData={setState} visibilityMode={state.visibilityMode} />
          </ErrorBoundary>
        </main>
        <AgentStatusBar
          agents={state.agents}
          jobs={state.jobs}
          timeline={state.timeline}
        />
      </div>
    </div>
  );
}

function upsertById(items, item) {
  const exists = items.some((current) => current.id === item.id);
  if (!exists) {
    return [item, ...items];
  }
  return items.map((current) => (current.id === item.id ? { ...current, ...item } : current));
}

function upsertByKey(items, item, key) {
  const exists = items.some((current) => current[key] === item[key]);
  if (!exists) {
    return [item, ...items];
  }
  return items.map((current) => (current[key] === item[key] ? { ...current, ...item } : current));
}
