import { useEffect, useState } from "react";
import { api } from "../services/api";
import BuildTimeline from "../components/workspace/BuildTimeline";
import WorkspaceHealth from "../components/workspace/WorkspaceHealth";
import FileExplorer from "../components/workspace/FileExplorer";
import BuildMetrics from "../components/workspace/BuildMetrics";
import TaskGraph from "../components/workspace/TaskGraph";
import BuildReplay from "../components/workspace/BuildReplay";
import FailureDiagnostics from "../components/workspace/FailureDiagnostics";
import ProjectEditor from "../components/workspace/ProjectEditor";
import EditTimeline from "../components/workspace/EditTimeline";
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
  const buildEvents = data?.buildEvents || [];

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
    api.getWorkspaceArchive().then(setArchive).catch(() => {});
  }

  // ── Derived Data ──────────────────────────────────
  const relatedTasks = tasks.filter((task) => task && task.workspace_id === effectiveWorkspaceId);
  const runningTasks = relatedTasks.filter(t => ["Running", "Reviewing"].includes(t.status)).length;
  const completedTasks = relatedTasks.filter(t => t.status === "Completed").length;
  const failedTasks = relatedTasks.filter(t => t.status === "Failed");
  const remainingTasks = relatedTasks.length - completedTasks - runningTasks;

  const workspaceActivity = activity.filter(
    (event) => event && (
      (event.type || "").startsWith("WORKSPACE_") ||
      (event.type || "").startsWith("TASK_") ||
      (event.type || "").startsWith("BUILD_") ||
      (event.source || "").includes("Workspace") ||
      (event.source || "").includes("Builder") ||
      (event.source || "").includes("Architect")
    )
  );

  const generatedFiles = relatedTasks
    .filter(t => t.output_files && t.output_files.length > 0)
    .flatMap(t => t.output_files);

  const activeAgents = agents.filter(a =>
    a.status === "Running" || a.status === "Thinking" || a.status === "Reviewing"
  );

  const isCompleted = workspace?.status === "Completed";
  const hasFailed = failedTasks.length > 0;

  return (
    <div className="build-center">
      {/* ── S1: Create Workspace & Open Project ───────── */}
      <section className="bc-two-col bc-stagger-1">
        <div className="bc-form-card">
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
        </div>
        
        <ProjectEditor onCreateWorkspace={(newDraft, analysis) => {
          api.createWorkspace(newDraft).then(created => {
            api.updateProjectContext(created.id, {
              project_name: analysis.project_name,
              framework: analysis.framework
            });
            setData((current) => ({ ...current, workspaces: [created, ...current.workspaces] }));
            setSelectedWorkspaceId(created.id);
          });
        }} />
      </section>

      {/* ── S2: Workspace Tabs ────────────────────────── */}
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

      {/* ── Build Center Core ────────────────────────── */}
      {workspace && (
        <>
          {/* ── S3: Hero + Progress ────────────────────── */}
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
                <button className="bc-hero-btn bc-hero-btn-primary" onClick={() => {}}>
                  Open Workspace
                </button>
                <button className="bc-hero-btn bc-hero-btn-danger" onClick={() => deleteWorkspace(workspace.id)}>
                  Delete
                </button>
              </div>
            </div>

            <div className="bc-progress-card">
              <div className="bc-progress-header">
                <h3 className="bc-progress-title">Build Progress</h3>
                <span className="bc-progress-percent">{workspace.progress ?? 0}%</span>
              </div>
              <div className="ui-progress-container">
                <div className="ui-progress-bar" style={{ width: `${workspace.progress ?? 0}%`, transition: 'width 0.8s ease' }}></div>
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

          {/* ── S4: Build Metrics (F5) ───────────────────── */}
          <section className="bc-stagger-4">
            <BuildMetrics tasks={relatedTasks} workspace={workspace} />
          </section>

          {/* ── S5: Active Agents ─────────────────────────── */}
          {activeAgents.length > 0 && (
            <section className="bc-agents bc-stagger-5">
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

          {/* ── S6: Task Pipeline (F6) ───────────────────── */}
          <section className="bc-stagger-6">
            <TaskGraph tasks={relatedTasks} />
          </section>

          {/* ── S7: Timeline + File Explorer (F2, F4, F7) ── */}
          <section className="bc-two-col bc-stagger-7">
            <BuildTimeline
              activity={workspaceActivity}
              buildEvents={buildEvents}
              workspaceId={effectiveWorkspaceId}
            />
            <FileExplorer tasks={relatedTasks} />
          </section>

          {/* ── S8: Workspace Health (F3) ─────────────────── */}
          <section className="bc-stagger-8">
            <WorkspaceHealth
              tasks={relatedTasks}
              activity={workspaceActivity}
              workspace={workspace}
            />
          </section>

          {/* ── S9: Failure Diagnostics (F9) — conditional ── */}
          {hasFailed && (
            <section className="bc-stagger-9">
              <FailureDiagnostics tasks={relatedTasks} activity={workspaceActivity} />
            </section>
          )}

          {/* ── S10: Build Replay (F8) — for builds with history ── */}
          {(isCompleted || completedTasks > 0) && (
            <section className="bc-stagger-10">
              <BuildReplay tasks={relatedTasks} workspace={workspace} />
            </section>
          )}

          {/* ── S11: Edit Timeline (F11) ────────────────── */}
          <EditTimeline workspaceId={effectiveWorkspaceId} />
        </>
      )}

      {/* ── Archive ──────────────────────────────────── */}
      {archive.length > 0 && (
        <section className="wi-section" style={{ marginTop: "var(--space-8)" }}>
          <div className="wi-section-header">
            <h3 className="wi-section-title">Completed Projects</h3>
            <span className="wi-section-badge">{archive.length}</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-8)" }}>
            {archive.map((entry) => {
              const entryStatusStyle = STATUS_COLORS[entry.status] || DEFAULT_STATUS_STYLE;
              return (
                <div
                  key={entry.id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "var(--space-12) var(--space-16)",
                    background: "rgba(255,255,255,0.02)",
                    borderRadius: "var(--radius-md)",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  <div>
                    <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                      {entry.project_name || "Unnamed"}
                    </span>
                    <span style={{ fontSize: "var(--text-xs)", opacity: 0.6, marginLeft: "var(--space-8)" }}>
                      {entry.path || "—"}
                    </span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "var(--space-8)" }}>
                    <span style={{ fontSize: "var(--text-xs)", opacity: 0.6 }}>
                      {entry.tasks_completed}/{entry.task_count} tasks
                    </span>
                    <span
                      className="ui-status-pill"
                      style={{ background: entryStatusStyle.bg, color: entryStatusStyle.color }}
                    >
                      <span className="dot"></span>
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
