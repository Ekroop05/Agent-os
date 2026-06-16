import ActivityFeed from "../components/ActivityFeed";

const STATUS_COLORS = {
  Planning: "#7dd3fc",
  Building: "#c4b5fd",
  Reviewing: "#fde68a",
  Completed: "#86efac",
  Failed: "#fca5a5",
};

export default function Dashboard({ data }) {
  const agents = data?.agents || [];
  const tasks = data?.tasks || [];
  const workspaces = data?.workspaces || [];
  const activity = data?.activity || [];
  const systemStatus = data?.systemStatus;

  const activeAgents = systemStatus?.active_agents ?? agents.filter((agent) => agent && agent.status === "Running").length;
  const activeTasks = systemStatus?.active_tasks ?? tasks.filter((task) => task && task.status && ["Running", "Reviewing"].includes(task.status)).length;
  // P8: Use status field (not build_status)
  const activeWorkspaces = systemStatus?.active_workspaces ?? workspaces.filter(
    (ws) => ws && ws.status && ["Building", "Reviewing", "Planning"].includes(ws.status)
  ).length;

  return (
    <div className="dashboard-grid">
      <section className="stat-grid">
        <Stat label="Active Agents" value={activeAgents} />
        <Stat label="Active Tasks" value={activeTasks} />
        <Stat label="Active Workspaces" value={activeWorkspaces} />
        <Stat label="Recent Activity" value={activity.length} />
      </section>

      <div className="panel-grid">
        <ActivityFeed logs={activity} limit={8} />
        <section className="panel scroll-panel">
          <div className="section-heading">
            <h2>Current Workspaces</h2>
            <span>{workspaces.length}</span>
          </div>
          <div className="sandbox-list">
            {workspaces.length ? workspaces.slice(0, 5).map((workspace) => (
              <div className="state-row" key={workspace?.id || Math.random()}>
                <span>{workspace?.project_name || workspace?.name || "Unnamed"}</span>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span
                    className={`status-pill ${(workspace?.status || "planning").toLowerCase()}`}
                    style={{ fontSize: "0.7rem", padding: "2px 8px" }}
                  >
                    {workspace?.status || "Planning"}
                  </span>
                  <strong>{workspace?.progress ?? 0}%</strong>
                </div>
              </div>
            )) : <p className="panel-copy">No approved workspaces yet.</p>}
          </div>
        </section>
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <article className="stat-card">
      <span>{label}</span>
      <strong>{value ?? 0}</strong>
    </article>
  );
}

