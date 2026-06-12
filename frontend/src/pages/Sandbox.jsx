import { useEffect, useState } from "react";
import { api } from "../services/api";

const STATUS_COLORS = {
  Planning: { bg: "rgba(56, 189, 248, 0.15)", color: "#7dd3fc", icon: "📋" },
  Building: { bg: "rgba(139, 92, 246, 0.15)", color: "#c4b5fd", icon: "🔨" },
  Reviewing: { bg: "rgba(245, 158, 11, 0.15)", color: "#fde68a", icon: "🔍" },
  Completed: { bg: "rgba(34, 197, 94, 0.2)", color: "#86efac", icon: "✅" },
  Failed: { bg: "rgba(248, 113, 113, 0.2)", color: "#fca5a5", icon: "❌" },
};

export default function Sandbox({ data, setData, visibilityMode }) {
  const [draftRoot, setDraftRoot] = useState(data.sandbox?.project_root || "D:/Projects");
  const [error, setError] = useState("");

  useEffect(() => {
    setDraftRoot(data.sandbox?.project_root || "D:/Projects");
  }, [data.sandbox?.project_root]);

  async function saveRoot(event) {
    event.preventDefault();
    setError("");
    try {
      const sandbox = await api.updateSandboxSettings(draftRoot);
      setData((current) => ({ ...current, sandbox }));
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  const sandbox = data.sandbox || { project_root: "D:/Projects", projects: [], workspace_mappings: [] };
  const workspaces = data.workspaces || [];
  const buildEvents = data.buildEvents || [];
  const isDeveloper = visibilityMode === "Developer";

  // Group build events by workspace
  function eventsForWorkspace(workspaceId) {
    return buildEvents
      .filter((e) => e.workspace_id === workspaceId)
      .slice(0, 15);
  }

  // Get tasks for a workspace
  function tasksForWorkspace(workspaceId) {
    return (data.tasks || []).filter((t) => t.workspace_id === workspaceId);
  }

  return (
    <div className="sandbox-execution-page">
      {/* ── Project Root Config ─────────────────────── */}
      <section className="panel sandbox-config-panel">
        <div className="section-heading">
          <h2>Project Root</h2>
          <span>{sandbox.project_root}</span>
        </div>
        <form className="inline-form" onSubmit={saveRoot}>
          <input
            aria-label="Project root directory"
            value={draftRoot}
            onChange={(e) => setDraftRoot(e.target.value)}
          />
          <button type="submit">Save Root</button>
        </form>
        {error && <div className="system-alert">{error}</div>}
      </section>

      {/* ── Active Projects / Build Cards ──────────── */}
      {workspaces.length === 0 ? (
        <section className="panel sandbox-empty-panel">
          <div className="sandbox-empty-state">
            <div className="empty-icon">🚀</div>
            <h3>No Projects Yet</h3>
            <p className="panel-copy">
              Head to the Architect page to plan and approve a project. Once approved,
              the build pipeline will start automatically and progress will appear here.
            </p>
          </div>
        </section>
      ) : (
        <div className="build-cards-grid">
          {workspaces.map((ws) => {
            const statusStyle = STATUS_COLORS[ws.build_status] || STATUS_COLORS.Planning;
            const wsTasks = tasksForWorkspace(ws.id);
            const completedTasks = wsTasks.filter((t) => t.status === "Completed").length;
            const totalTasks = wsTasks.length || ws.task_count || 0;
            const progress = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : (ws.progress || 0);
            const wsEvents = eventsForWorkspace(ws.id);

            return (
              <div className="build-card" key={ws.id}>
                {/* Card Header */}
                <div className="build-card-header">
                  <div className="build-card-title">
                    <h3>{ws.name}</h3>
                    <span
                      className="build-status-badge"
                      style={{ background: statusStyle.bg, color: statusStyle.color }}
                    >
                      {statusStyle.icon} {ws.build_status || "Planning"}
                    </span>
                  </div>
                  <p className="build-card-path">{ws.path}</p>
                </div>

                {/* Progress Ring + Stats */}
                <div className="build-progress-section">
                  <div className="build-progress-ring-container">
                    <svg className="build-progress-ring" viewBox="0 0 120 120">
                      <circle
                        className="progress-ring-bg"
                        cx="60" cy="60" r="52"
                        fill="none" stroke="rgba(148,163,184,0.12)" strokeWidth="8"
                      />
                      <circle
                        className="progress-ring-fill"
                        cx="60" cy="60" r="52"
                        fill="none"
                        stroke={statusStyle.color}
                        strokeWidth="8"
                        strokeLinecap="round"
                        strokeDasharray={`${progress * 3.267} 326.7`}
                        transform="rotate(-90 60 60)"
                      />
                    </svg>
                    <div className="progress-ring-label">
                      <strong>{progress}%</strong>
                      <span>Progress</span>
                    </div>
                  </div>

                  <div className="build-stats">
                    <div className="build-stat">
                      <span className="build-stat-label">Tasks</span>
                      <strong>{completedTasks}/{totalTasks}</strong>
                    </div>
                    <div className="build-stat">
                      <span className="build-stat-label">ETA</span>
                      <strong>
                        {ws.estimated_completion_minutes
                          ? `${ws.estimated_completion_minutes} min`
                          : progress >= 100 ? "Done" : "Calculating..."}
                      </strong>
                    </div>
                    <div className="build-stat">
                      <span className="build-stat-label">Current Agent</span>
                      <strong className="build-agent-name">
                        {ws.current_agent || "—"}
                      </strong>
                    </div>
                    <div className="build-stat">
                      <span className="build-stat-label">Current Task</span>
                      <strong>{ws.current_task_title || "—"}</strong>
                    </div>
                  </div>
                </div>

                {/* Linear Progress Bar */}
                <div className="build-linear-progress">
                  <div
                    className="build-linear-fill"
                    style={{
                      width: `${progress}%`,
                      background: `linear-gradient(90deg, ${statusStyle.color}88, ${statusStyle.color})`,
                    }}
                  />
                </div>

                {/* Task List (Developer Mode) */}
                {isDeveloper && wsTasks.length > 0 && (
                  <div className="build-task-list">
                    <h4>Tasks</h4>
                    {wsTasks.map((task) => (
                      <div className="build-task-row" key={task.id}>
                        <span className={`build-task-status ${task.status.toLowerCase()}`}>
                          {task.status === "Completed" ? "✓" : task.status === "Running" ? "▶" : task.status === "Failed" ? "✗" : "○"}
                        </span>
                        <span className="build-task-title">{task.title}</span>
                        {task.security_status && task.security_status !== "Pending" && (
                          <span className={`build-security-badge ${task.security_status.toLowerCase()}`}>
                            {task.security_status}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Live Activity Stream */}
                {isDeveloper && wsEvents.length > 0 && (
                  <div className="build-activity-stream">
                    <h4>Live Activity</h4>
                    <div className="build-activity-list">
                      {wsEvents.map((event, index) => (
                        <div className="build-activity-item" key={index}>
                          <span className={`activity-dot ${event.approved !== undefined ? (event.approved ? 'success' : 'warning') : 'info'}`} />
                          <span className="build-activity-text">
                            {event.title
                              ? `${event.title} — ${event.approved !== undefined ? (event.approved ? "Approved" : "Rejected") : ""}`
                              : JSON.stringify(event).slice(0, 80)
                            }
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Executive Mode - Simplified View */}
                {!isDeveloper && (
                  <div className="build-executive-summary">
                    <div className="executive-phase-bar">
                      {["Planning", "Building", "Reviewing", "Completed"].map((phase) => (
                        <div
                          key={phase}
                          className={`executive-phase ${
                            ws.build_status === phase ? "active" :
                            ["Planning", "Building", "Reviewing", "Completed"].indexOf(phase) <
                            ["Planning", "Building", "Reviewing", "Completed"].indexOf(ws.build_status || "Planning")
                              ? "done" : ""
                          }`}
                        >
                          <div className="phase-dot" />
                          <span>{phase}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ── Existing Projects on Disk ─────────────── */}
      {sandbox.projects.length > 0 && (
        <section className="panel">
          <div className="section-heading">
            <h2>Projects on Disk</h2>
            <span>{sandbox.projects.length}</span>
          </div>
          <div className="sandbox-list">
            {sandbox.projects.map((project) => (
              <div className="state-row" key={project.path}>
                <span>{project.name}</span>
                <strong>{project.path}</strong>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
