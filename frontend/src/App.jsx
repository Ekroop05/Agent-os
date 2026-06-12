import { useEffect, useMemo, useState } from "react";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import Activity from "./pages/Activity";
import Agents from "./pages/Agents";
import Architect from "./pages/Architect";
import Dashboard from "./pages/Dashboard";
import Sandbox from "./pages/Sandbox";
import Settings from "./pages/Settings";
import Tasks from "./pages/Tasks";
import Workspaces from "./pages/Workspaces";
import { api } from "./services/api";
import { connectChannel } from "./services/websocket";

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
    error: "",
    visibilityMode: "Developer",
  });

  useEffect(() => {
    async function load() {
      const [agents, tasks, workspaces, activity, sandbox, systemStatus] = await Promise.all([
        api.getAgents(),
        api.getTasks(),
        api.getWorkspaces(),
        api.getActivity(),
        api.getSandbox(),
        api.getSystemStatus(),
      ]);

      setState((current) => ({
        ...current,
        agents,
        tasks,
        workspaces,
        activity,
        sandbox,
        systemStatus,
        error: "",
      }));
    }

    load().catch((error) => {
      setState((current) => ({
        ...current,
        error: `Backend unavailable: ${error.message}`,
      }));
    });
  }, []);

  useEffect(() => {
    const onPopState = () => setPath(getPath());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    const activitySocket = connectChannel("activity", (event) => {
      setState((current) => ({
        ...current,
        activity: [event, ...current.activity].slice(0, 80),
      }));
    });

    const agentSocket = connectChannel("agents", (event) => {
      setState((current) => ({
        ...current,
        agents: upsertById(current.agents, event),
      }));
    });

    const taskSocket = connectChannel("tasks", (event) => {
      setState((current) => ({
        ...current,
        tasks: upsertById(current.tasks, event),
      }));
    });

    const workspaceSocket = connectChannel("workspaces", (event) => {
      setState((current) => ({
        ...current,
        workspaces: event.deleted
          ? current.workspaces.filter((workspace) => workspace.id !== event.id)
          : upsertById(current.workspaces, event),
      }));
    });

    const systemSocket = connectChannel("system", (event) => {
      setState((current) => ({
        ...current,
        systemStatus: event,
      }));
    });

    const buildSocket = connectChannel("build", (event) => {
      setState((current) => ({
        ...current,
        buildEvents: [event, ...current.buildEvents].slice(0, 100),
      }));

      // Also refresh workspaces when build progress updates
      if (event.workspace_id) {
        api.getWorkspaces().then((workspaces) => {
          setState((current) => ({ ...current, workspaces }));
        }).catch(() => {});
      }
    });

    return () => {
      activitySocket?.close();
      agentSocket?.close();
      taskSocket?.close();
      workspaceSocket?.close();
      systemSocket?.close();
      buildSocket?.close();
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
    <div className="app-shell">
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
          <CurrentPage data={state} setData={setState} visibilityMode={state.visibilityMode} />
        </main>
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
