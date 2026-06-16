import { useEffect, useState } from "react";
import { api } from "../services/api";

const STATUS_COLORS = {
  Planning: { bg: "rgba(56, 189, 248, 0.15)", color: "#7dd3fc" },
  Building: { bg: "rgba(139, 92, 246, 0.15)", color: "#c4b5fd" },
  Reviewing: { bg: "rgba(245, 158, 11, 0.15)", color: "#fde68a" },
  Completed: { bg: "rgba(34, 197, 94, 0.2)", color: "#86efac" },
  Failed: { bg: "rgba(248, 113, 113, 0.2)", color: "#fca5a5" },
};

const DEFAULT_STATUS_STYLE = { bg: "rgba(148, 163, 184, 0.15)", color: "#94a3b8" };

export default function Workspaces({ data, setData }) {
  const workspaces = data?.workspaces || [];
  const tasks = data?.tasks || [];
  const agents = data?.agents || [];
  const activity = data?.activity || [];

  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState(workspaces[0]?.id);
  const [draft, setDraft] = useState({ name: "", description: "", active_agents: 1 });
  const [archive, setArchive] = useState([]);

  const effectiveWorkspaceId = selectedWorkspaceId || workspaces[0]?.id;
  const workspace = workspaces.find((item) => item.id === effectiveWorkspaceId) || workspaces[0];

  // Load archive on mount
  useEffect(() => {
    api.getWorkspaceArchive()
      .then(setArchive)
      .catch(() => setArchive([]));
  }, [workspaces.length]);

  async function createWorkspace(event) {
    event.preventDefault();
    const created = await api.createWorkspace(draft);
    setData((current) => ({ ...current, workspaces: [created, ...current.workspaces] }));
    setSelectedWorkspaceId(created.id);
    setDraft({ name: "", description: "", active_agents: 1 });
  }

  async function deleteWorkspace(workspaceId) {
    await api.deleteWorkspace(workspaceId);
    setData((current) => ({
      ...current,
      workspaces: current.workspaces.filter((item) => item.id !== workspaceId),
    }));
    setSelectedWorkspaceId(null);
    // Refresh archive
    api.getWorkspaceArchive().then(setArchive).catch(() => {});
  }

  const relatedTasks = tasks.filter((task) => task && task.status && task.workspace_id === effectiveWorkspaceId);
  const timeline = activity.filter(
    (event) => event && ((event.type || "").startsWith("WORKSPACE_") || (event.source || "").includes("Workspace"))
  );

  return (
    <div className="workspace-page">
      <form className="inline-form" onSubmit={createWorkspace}>
        <input
          placeholder="Workspace name"
          value={draft.name}
          onChange={(event) => setDraft({ ...draft, name: event.target.value })}
          required
        />
        <input
          placeholder="Description"
          value={draft.description}
          onChange={(event) => setDraft({ ...draft, description: event.target.value })}
          required
        />
        <input
          min="0"
          type="number"
          value={draft.active_agents}
          onChange={(event) => setDraft({ ...draft, active_agents: Number(event.target.value) })}
        />
        <button type="submit">Create Workspace</button>
      </form>

      <section className="workspace-card-grid">
        {workspaces.map((item) => {
          if (!item || !item.id) return null;
          const statusStyle = STATUS_COLORS[item.status] || DEFAULT_STATUS_STYLE;
          return (
            <button
              className="workspace-card"
              key={item.id}
              type="button"
              onClick={() => setSelectedWorkspaceId(item.id)}
            >
              <span
                className="status-pill"
                style={{ background: statusStyle.bg, color: statusStyle.color }}
              >
                {item.status || "Planning"}
              </span>
              <h3>{item.project_name || item.name || "Unnamed"}</h3>
              <p>{item.active_agents ?? 0} agents / {item.task_count ?? 0} tasks / {item.progress ?? 0}%</p>
              <p style={{ fontSize: "0.75rem", opacity: 0.7 }}>{item.path || "—"}</p>
              <small>Created {item.created_at || "—"}</small>
            </button>
          );
        })}
      </section>

      {workspace && (
        <section className="detail-panel">
          <div className="section-heading">
            <h2>{workspace.project_name || workspace.name || "Unnamed"}</h2>
            <span
              className="status-pill"
              style={{
                background: (STATUS_COLORS[workspace.status] || DEFAULT_STATUS_STYLE).bg,
                color: (STATUS_COLORS[workspace.status] || DEFAULT_STATUS_STYLE).color,
              }}
            >
              {workspace.status || "Planning"}
            </span>
          </div>
          <div className="agent-actions">
            <button type="button" onClick={() => setSelectedWorkspaceId(workspace.id)}>Open Workspace</button>
            <button type="button" onClick={() => deleteWorkspace(workspace.id)}>Delete Workspace</button>
          </div>

          <div className="detail-grid">
            {/* P3: Workspace Metadata — single source of truth */}
            <Detail title="Workspace Metadata" items={[
              `Project: ${workspace.project_name || workspace.name || "—"}`,
              `Slug: ${workspace.slug || "—"}`,
              `Path: ${workspace.path || "—"}`,
              `Status: ${workspace.status || "—"}`,
              `Progress: ${workspace.progress ?? 0}%`,
              `Created: ${workspace.created_at || "—"}`,
            ]} />
            <Detail title="Active Agents" items={agents.filter((agent) => agent && agent.status === "Running").map((agent) => agent.name || "Unnamed")} />
            <Detail title="Workspace Tasks" items={relatedTasks.map((task) => `${task.title || "Untitled"} — ${task.status || "Pending"}`)} />
            <Detail title="Activity Timeline" items={timeline.length ? timeline.map((event) => event.message || "Event") : ["No workspace events yet"]} />
          </div>
        </section>
      )}

      {/* P9: Completed Projects Archive */}
      {archive.length > 0 && (
        <section className="panel" style={{ marginTop: "1.5rem" }}>
          <div className="section-heading">
            <h2>Completed Projects</h2>
            <span>{archive.length}</span>
          </div>
          <div className="sandbox-list">
            {archive.map((entry) => {
              const entryStatusStyle = STATUS_COLORS[entry.status] || DEFAULT_STATUS_STYLE;
              return (
                <div className="state-row" key={entry.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <span style={{ fontWeight: 600 }}>{entry.project_name || "Unnamed"}</span>
                    <span style={{ fontSize: "0.75rem", opacity: 0.6, marginLeft: "0.5rem" }}>{entry.path || "—"}</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <span style={{ fontSize: "0.7rem", opacity: 0.6 }}>
                      {entry.tasks_completed}/{entry.task_count} tasks
                    </span>
                    <span
                      className="status-pill"
                      style={{ background: entryStatusStyle.bg, color: entryStatusStyle.color, fontSize: "0.7rem", padding: "2px 8px" }}
                    >
                      {entry.status}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}

function Detail({ title, items }) {
  const safeItems = (items || []).filter((item) => item != null);
  return (
    <div className="detail-block">
      <h3>{title}</h3>
      {safeItems.length ? safeItems.map((item) => <p key={item}>{item}</p>) : <p>None</p>}
    </div>
  );
}
