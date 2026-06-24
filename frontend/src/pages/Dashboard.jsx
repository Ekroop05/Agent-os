import './Dashboard.css';

const AGENT_ROLES = [
  { name: "Architect", role: "Plans architecture and decomposes requirements into tasks." },
  { name: "Builder", role: "Generates code files from task specifications." },
  { name: "QA", role: "Reviews code quality, runs validation checks." },
  { name: "Security", role: "Scans for vulnerabilities and enforces security policy." },
];

export default function Dashboard({ data }) {
  const agents = data?.agents || [];
  const tasks = data?.tasks || [];
  const workspaces = data?.workspaces || [];
  const activity = data?.activity || [];
  const systemStatus = data?.systemStatus;

  const activeAgents = systemStatus?.active_agents ?? agents.filter((a) => a && a.status === "Running").length;
  const activeTasks = systemStatus?.active_tasks ?? tasks.filter((t) => t && t.status && ["Running", "Reviewing"].includes(t.status)).length;
  const activeWorkspaces = systemStatus?.active_workspaces ?? workspaces.filter(
    (ws) => ws && ws.status && ["Building", "Reviewing", "Planning"].includes(ws.status)
  ).length;
  const completedTasks = tasks.filter((t) => t && t.status === "Completed").length;
  const successRate = tasks.length > 0 ? Math.round((completedTasks / tasks.length) * 100) : 100;

  // Build agent cards from live data, falling back to role descriptions
  const agentCards = AGENT_ROLES.map((role) => {
    const live = agents.find((a) => a && a.name && a.name.includes(role.name));
    return {
      name: role.name,
      status: live?.status || "Idle",
      task: live?.current_task || role.role,
    };
  });

  // Current workspace (most recent active)
  const currentWorkspace = workspaces.find(
    (ws) => ws && ws.status && ["Building", "Reviewing", "Planning"].includes(ws.status)
  ) || workspaces[0];

  return (
    <div className="dashboard-v2">
      {/* ── Hero ──────────────────────────────────── */}
      <section className="dash-hero dash-stagger-1">
        <div className="dash-hero-content">
          <span className="dash-hero-eyebrow">Command Center</span>
          <h2 className="dash-hero-title">
            {currentWorkspace ? currentWorkspace.name : "Agent OS"}
          </h2>
          <p className="dash-hero-subtitle">
            {currentWorkspace
              ? `Workspace is ${(currentWorkspace.status || "idle").toLowerCase()} · ${currentWorkspace.progress ?? 0}% complete`
              : "Multi-agent AI runtime — design, build, test, and ship software autonomously."}
          </p>
          <div className="dash-hero-actions">
            <button className="dash-hero-btn dash-hero-btn-primary" type="button">
              New Project
            </button>
            <button className="dash-hero-btn dash-hero-btn-secondary" type="button">
              View Workspaces
            </button>
          </div>
        </div>
        <div className="dash-hero-stats">
          <div className="dash-hero-stat">
            <span className="dash-hero-stat-value">{activeAgents}</span>
            <span className="dash-hero-stat-label">Active Agents</span>
          </div>
          <div className="dash-hero-stat">
            <span className="dash-hero-stat-value">{activeTasks}</span>
            <span className="dash-hero-stat-label">Running Tasks</span>
          </div>
        </div>
      </section>

      {/* ── Stat Cards ────────────────────────────── */}
      <section className="dash-stats-row dash-stagger-2">
        <StatCard label="Active Agents" value={activeAgents} />
        <StatCard label="Running Tasks" value={activeTasks} />
        <StatCard label="Workspaces" value={workspaces.length} />
        <StatCard label="Success Rate" value={`${successRate}%`} />
        <StatCard label="Activity Events" value={activity.length} />
      </section>

      {/* ── Agent Overview ────────────────────────── */}
      <section className="dash-stagger-3">
        <h3 className="dash-section-title">Agent Overview</h3>
        <div className="dash-agents-grid">
          {agentCards.map((agent) => (
            <div className="dash-agent-card" key={agent.name}>
              <div className="dash-agent-header">
                <span className="dash-agent-name">{agent.name}</span>
                <span className={`ui-status-pill ${agent.status.toLowerCase()}`}>
                  <span className="dot" aria-hidden="true"></span>
                  {agent.status}
                </span>
              </div>
              <span className="dash-agent-task">{agent.task}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ── Activity + Workspaces ─────────────────── */}
      <section className="dash-two-col dash-stagger-4">
        {/* Activity Feed */}
        <div className="dash-panel">
          <div className="dash-panel-header">
            <h3 className="dash-panel-title">Recent Activity</h3>
            <span className="dash-panel-badge">{activity.length}</span>
          </div>
          <div className="dash-activity-list">
            {activity.length > 0 ? activity.slice(0, 10).map((log, idx) => (
              <div className="dash-activity-item" key={log.id || idx}>
                <span className={`dash-activity-dot ${log.severity || "info"}`} />
                <div className="dash-activity-text">
                  <p>{log.message}</p>
                  <small>{log.source} · {log.timestamp}</small>
                </div>
              </div>
            )) : (
              <div className="dash-empty">No activity yet. Start a project to see events here.</div>
            )}
          </div>
        </div>

        {/* Workspaces */}
        <div className="dash-panel">
          <div className="dash-panel-header">
            <h3 className="dash-panel-title">Workspaces</h3>
            <span className="dash-panel-badge">{workspaces.length}</span>
          </div>
          <div className="dash-workspace-list">
            {workspaces.length > 0 ? workspaces.slice(0, 6).map((ws) => (
              <div className="dash-workspace-row" key={ws.id}>
                <span className="dash-workspace-name">{ws.project_name || ws.name || "Unnamed"}</span>
                <div className="dash-workspace-meta">
                  <span className={`ui-status-pill ${(ws.status || "planning").toLowerCase()}`}>
                    <span className="dot" aria-hidden="true"></span>
                    {ws.status || "Planning"}
                  </span>
                  <span className="dash-workspace-progress">{ws.progress ?? 0}%</span>
                </div>
              </div>
            )) : (
              <div className="dash-empty">No approved workspaces yet.</div>
            )}
          </div>
        </div>
      </section>

      {/* ── System Health ─────────────────────────── */}
      <section className="dash-stagger-5">
        <h3 className="dash-section-title">System Health</h3>
        <div className="dash-panel">
          <div className="dash-health-grid">
            <HealthMeter label="CPU Usage" value={systemStatus?.cpu_percent ?? 24} />
            <HealthMeter label="Memory" value={systemStatus?.memory_percent ?? 38} />
            <HealthMeter label="Disk" value={systemStatus?.disk_percent ?? 52} />
            <HealthMeter label="Agent Availability" value={agents.length > 0 ? Math.round((agents.filter((a) => a.status !== "Error").length / agents.length) * 100) : 100} />
          </div>
        </div>
      </section>

      {/* ── Metrics Footer ────────────────────────── */}
      <section className="dash-stats-row dash-stagger-6">
        <StatCard label="Total Agents" value={agents.length} />
        <StatCard label="Total Tasks" value={tasks.length} />
        <StatCard label="Completed" value={completedTasks} />
        <StatCard label="Active Workspaces" value={activeWorkspaces} />
        <StatCard label="Uptime" value={systemStatus?.uptime || "–"} />
      </section>
    </div>
  );
}

function StatCard({ label, value }) {
  return (
    <article className="dash-stat-card">
      <div className="dash-stat-label">{label}</div>
      <div className="dash-stat-value">{value ?? 0}</div>
    </article>
  );
}

function HealthMeter({ label, value }) {
  const safeVal = Math.min(Math.max(value, 0), 100);
  return (
    <div className="dash-health-item">
      <div className="dash-health-label">
        <span className="dash-health-name">{label}</span>
        <span className="dash-health-value">{safeVal}%</span>
      </div>
      <div className="ui-progress-container">
        <div className="ui-progress-bar" style={{ width: `${safeVal}%` }} />
      </div>
    </div>
  );
}
