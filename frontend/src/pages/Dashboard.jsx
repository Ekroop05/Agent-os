import ActivityFeed from "../components/ActivityFeed";

export default function Dashboard({ data }) {
  const agents = data?.agents || [];
  const tasks = data?.tasks || [];
  const workspaces = data?.workspaces || [];
  const activity = data?.activity || [];
  const systemStatus = data?.systemStatus;

  const activeAgents = systemStatus?.active_agents ?? agents.filter((agent) => agent && agent.status === "Running").length;
  const activeTasks = systemStatus?.active_tasks ?? tasks.filter((task) => task && task.status && ["Running", "Reviewing"].includes(task.status)).length;
  const activeWorkspaces = systemStatus?.active_workspaces ?? workspaces.filter((workspace) => workspace && workspace.status === "Active").length;

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
                <span>{workspace?.name || "Unnamed"}</span>
                <strong>{workspace?.path || "—"}</strong>
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
