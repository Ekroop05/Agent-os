import { useEffect, useState } from "react";
import { api } from "../services/api";
import "./Workspaces.css";

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
    api.getWorkspaceArchive().then(setArchive).catch(() => {});
  }

  const relatedTasks = tasks.filter((task) => task && task.workspace_id === effectiveWorkspaceId);
  const runningTasks = relatedTasks.filter(t => ["Running", "Reviewing"].includes(t.status)).length;
  const completedTasks = relatedTasks.filter(t => t.status === "Completed").length;
  const remainingTasks = relatedTasks.length - completedTasks - runningTasks;

  const timeline = activity.filter(
    (event) => event && ((event.type || "").startsWith("WORKSPACE_") || (event.source || "").includes("Workspace"))
  );

  // Collect all generated files from completed tasks
  const generatedFiles = relatedTasks
    .filter(t => t.output_files && t.output_files.length > 0)
    .flatMap(t => t.output_files);

  // Active agents involved in this workspace (or system wide if none mapped directly)
  // Since agent-to-workspace mapping isn't strict yet, just show active agents
  const activeAgents = agents.filter(a => a.status === "Running" || a.status === "Thinking" || a.status === "Reviewing");

  return (
    <div className="build-center">
      {/* ── Create Workspace ───────────────────────────── */}
      <section className="bc-form-card bc-stagger-1">
        <h3>New Build</h3>
        <form className="bc-form" onSubmit={createWorkspace}>
          <input
            placeholder="Project name"
            value={draft.name}
            onChange={(event) => setDraft({ ...draft, name: event.target.value })}
            required
          />
          <input
            placeholder="Objective / Description"
            value={draft.description}
            onChange={(event) => setDraft({ ...draft, description: event.target.value })}
            required
          />
          <input
            min="1"
            type="number"
            value={draft.active_agents}
            onChange={(event) => setDraft({ ...draft, active_agents: Number(event.target.value) })}
            title="Active Agents"
          />
          <button type="submit">Start Build</button>
        </form>
      </section>

      {/* ── Workspace Tabs ─────────────────────────────── */}
      {workspaces.length > 0 && (
        <section className="bc-selector bc-stagger-2">
          {workspaces.map((item) => (
            <button
              key={item.id}
              className={`bc-selector-tab ${item.id === effectiveWorkspaceId ? "active" : ""}`}
              onClick={() => setSelectedWorkspaceId(item.id)}
            >
              {item.project_name || item.name || "Unnamed"}
            </button>
          ))}
        </section>
      )}

      {/* ── Build Center Core ──────────────────────────── */}
      {workspace && (
        <>
          <section className="bc-hero bc-stagger-3">
            <div className="bc-hero-main">
              <div className="bc-hero-header">
                <div>
                  <h2 className="bc-hero-title">{workspace.project_name || workspace.name || "Unnamed"}</h2>
                  <p className="bc-hero-subtitle">
                    {workspace.path || "No path assigned"} · Created {workspace.created_at || "recently"}
                  </p>
                </div>
                <span
                  className="ui-status-pill"
                  style={{
                    background: (STATUS_COLORS[workspace.status] || DEFAULT_STATUS_STYLE).bg,
                    color: (STATUS_COLORS[workspace.status] || DEFAULT_STATUS_STYLE).color,
                  }}
                >
                  <span className="dot"></span>
                  {workspace.status || "Planning"}
                </span>
              </div>
              <div className="bc-hero-actions">
                <button className="bc-hero-btn bc-hero-btn-primary" onClick={() => {/* Open IDE/Sandbox logic */}}>
                  Open Workspace
                </button>
                <button className="bc-hero-btn bc-hero-btn-danger" onClick={() => deleteWorkspace(workspace.id)}>
                  Delete
                </button>
              </div>
            </div>

            {/* Build Progress Card */}
            <div className="bc-progress-card">
              <div className="bc-progress-header">
                <h3 className="bc-progress-title">Build Progress</h3>
                <span className="bc-progress-percent">{workspace.progress ?? 0}%</span>
              </div>
              <div className="ui-progress-container">
                <div className="ui-progress-bar" style={{ width: `${workspace.progress ?? 0}%` }}></div>
              </div>
              <div className="bc-progress-stats">
                <div className="bc-progress-stat">
                  <span className="bc-progress-stat-val">{relatedTasks.length}</span>
                  <span className="bc-progress-stat-lbl">Total Tasks</span>
                </div>
                <div className="bc-progress-stat">
                  <span className="bc-progress-stat-val" style={{ color: "var(--status-success)" }}>{completedTasks}</span>
                  <span className="bc-progress-stat-lbl">Completed</span>
                </div>
                <div className="bc-progress-stat">
                  <span className="bc-progress-stat-val" style={{ color: "var(--color-primary)" }}>{runningTasks}</span>
                  <span className="bc-progress-stat-lbl">Running</span>
                </div>
                <div className="bc-progress-stat">
                  <span className="bc-progress-stat-val">{remainingTasks}</span>
                  <span className="bc-progress-stat-lbl">Remaining</span>
                </div>
              </div>
            </div>
          </section>

          {/* ── Active Agents Panel ──────────────────────── */}
          {activeAgents.length > 0 && (
            <section className="bc-agents bc-stagger-4">
              {activeAgents.map((agent) => (
                <div className="bc-agent-card running" key={agent.id}>
                  <div className="bc-agent-header">
                    <span className="bc-agent-name">{agent.name}</span>
                    <span className="ui-status-pill running">
                      <span className="dot"></span>
                      {agent.status}
                    </span>
                  </div>
                  <div className="bc-agent-task">{agent.current_task || agent.role}</div>
                </div>
              ))}
            </section>
          )}

          {/* ── Data Streams ─────────────────────────────── */}
          <section className="bc-three-col bc-stagger-5">
            {/* Task Stream */}
            <div className="bc-panel">
              <div className="bc-panel-header">
                <h3 className="bc-panel-title">Task Stream</h3>
                <span className="bc-panel-count">{relatedTasks.length}</span>
              </div>
              <div className="bc-scroll-area">
                {relatedTasks.length > 0 ? (
                  relatedTasks.slice().reverse().map(task => (
                    <div className="bc-stream-item" key={task.id}>
                      <div className="bc-stream-title">{task.title || "Untitled"}</div>
                      <div className="bc-stream-meta">
                        <span style={{ color: STATUS_COLORS[task.status]?.color || "inherit" }}>
                          {task.status || "Pending"}
                        </span>
                        <span>{task.assigned_agent || "Unassigned"}</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <p style={{ color: "var(--text-tertiary)" }}>No tasks yet.</p>
                )}
              </div>
            </div>

            {/* File Feed */}
            <div className="bc-panel">
              <div className="bc-panel-header">
                <h3 className="bc-panel-title">Generated Files</h3>
                <span className="bc-panel-count">{generatedFiles.length}</span>
              </div>
              <div className="bc-scroll-area">
                {generatedFiles.length > 0 ? (
                  generatedFiles.map((file, idx) => (
                    <div className="bc-file-item" key={`${file}-${idx}`}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                        <line x1="16" y1="13" x2="8" y2="13"></line>
                        <line x1="16" y1="17" x2="8" y2="17"></line>
                        <polyline points="10 9 9 9 8 9"></polyline>
                      </svg>
                      {file}
                    </div>
                  ))
                ) : (
                  <p style={{ color: "var(--text-tertiary)" }}>No files generated yet.</p>
                )}
              </div>
            </div>

            {/* Timeline */}
            <div className="bc-panel">
              <div className="bc-panel-header">
                <h3 className="bc-panel-title">Timeline</h3>
                <span className="bc-panel-count">{timeline.length}</span>
              </div>
              <div className="bc-scroll-area">
                {timeline.length > 0 ? (
                  timeline.slice().reverse().map((event, idx) => (
                    <div className="bc-timeline-item" key={event.id || idx}>
                      <div className="bc-timeline-dot"></div>
                      <div className="bc-timeline-content">
                        <p>{event.message || "Event"}</p>
                        <small>{event.timestamp || "Just now"}</small>
                      </div>
                    </div>
                  ))
                ) : (
                  <p style={{ color: "var(--text-tertiary)" }}>No timeline events.</p>
                )}
              </div>
            </div>
          </section>
        </>
      )}

      {/* Archive rendering preserved if needed... */}
    </div>
  );
}
