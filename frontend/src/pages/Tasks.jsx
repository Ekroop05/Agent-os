import { useState } from "react";
import { api } from "../services/api";
import "./Tasks.css";

const statuses = ["Pending", "Assigned", "Running", "Reviewing", "Blocked", "Completed", "Failed"];

const STATUS_ICONS = {
  Pending: "○",
  Assigned: "◎",
  Running: "▶",
  Reviewing: "🔍",
  Blocked: "⊘",
  Completed: "✓",
  Failed: "✗",
};

const SECURITY_COLORS = {
  Pending: { bg: "rgba(148,163,184,0.15)", color: "#94a3b8" },
  Reviewing: { bg: "rgba(245,158,11,0.15)", color: "#fde68a" },
  Approved: { bg: "rgba(34,197,94,0.2)", color: "#86efac" },
  Rejected: { bg: "rgba(248,113,113,0.2)", color: "#fca5a5" },
};
const DEFAULT_SECURITY_STYLE = { bg: "rgba(148,163,184,0.15)", color: "#94a3b8" };

export default function Tasks({ data, setData }) {
  const validTasks = (data?.tasks || []).filter(
    (t) => t && typeof t.id === "string" && typeof t.status === "string"
  );

  const [selectedTaskId, setSelectedTaskId] = useState(validTasks[0]?.id);
  const [draft, setDraft] = useState({
    title: "",
    description: "",
    assigned_agent: "Head Agent",
    priority: "Medium",
  });
  
  const effectiveTaskId = selectedTaskId || validTasks[0]?.id;
  const task = validTasks.find((item) => item.id === effectiveTaskId) || validTasks[0];

  async function createTask(event) {
    event.preventDefault();
    const created = await api.createTask(draft);
    setData((current) => ({ ...current, tasks: [created, ...current.tasks] }));
    setSelectedTaskId(created.id);
    setDraft({ title: "", description: "", assigned_agent: "Head Agent", priority: "Medium" });
  }

  async function updateStatus(status) {
    if (!task) return;
    const updated = await api.updateTask({ id: task.id, status });
    setData((current) => ({
      ...current,
      tasks: current.tasks.map((item) => (item.id === updated.id ? updated : item)),
    }));
  }

  const agents = data?.agents || [];

  return (
    <div className="tasks-v2">
      <section className="tasks-main-panel">
        <div className="tasks-header">
          <h2 className="tasks-title">Delegated Tasks</h2>
          <span className="tasks-count">{validTasks.length} tracked</span>
        </div>

        <form className="tasks-form" onSubmit={createTask}>
          <input
            placeholder="Task title"
            value={draft.title}
            onChange={(event) => setDraft({ ...draft, title: event.target.value })}
            required
          />
          <input
            placeholder="Description"
            value={draft.description}
            onChange={(event) => setDraft({ ...draft, description: event.target.value })}
            required
          />
          <select
            value={draft.assigned_agent}
            onChange={(event) => setDraft({ ...draft, assigned_agent: event.target.value })}
          >
            {agents.length > 0 ? (
              agents.map((agent) => (
                <option key={agent.id} value={agent.name}>{agent.name}</option>
              ))
            ) : (
              <option value="Head Agent">Head Agent</option>
            )}
          </select>
          <select value={draft.priority} onChange={(event) => setDraft({ ...draft, priority: event.target.value })}>
            <option>Low</option>
            <option>Medium</option>
            <option>High</option>
          </select>
          <button type="submit">Create</button>
        </form>

        <div className="tasks-table">
          <div className="tasks-table-header">
            <span>Task</span>
            <span>Agent</span>
            <span>Priority</span>
            <span>Status</span>
            <span>Created</span>
          </div>
          {validTasks.map((item, idx) => {
            const itemStatus = item.status || "Pending";
            return (
              <div
                className={`tasks-row ${item.id === effectiveTaskId ? "selected" : ""}`}
                key={item.id}
                onClick={() => setSelectedTaskId(item.id)}
                style={{ animation: `slideInRight 0.3s ease-out ${idx * 0.05}s both` }}
              >
                <span className="tasks-row-title" title={item.title || "Untitled"}>
                  {item.title || "Untitled"}
                </span>
                <span className="tasks-row-agent">{item.assigned_agent || "—"}</span>
                <span className="tasks-row-priority">{item.priority || "Medium"}</span>
                <span className={`ui-status-pill ${itemStatus.toLowerCase()}`}>
                  <span className="dot" aria-hidden="true"></span>
                  {itemStatus}
                </span>
                <span className="tasks-row-agent">{item.created_at || "—"}</span>
              </div>
            );
          })}
        </div>
      </section>

      {task && (
        <section className="tasks-detail-panel" key={task.id}>
          <div className="tasks-detail-header">
            <div>
              <h2 className="tasks-detail-title">{task.title || "Untitled"}</h2>
              <span className={`ui-status-pill ${(task.status || "pending").toLowerCase()}`}>
                <span className="dot" aria-hidden="true"></span>
                {task.status || "Pending"}
              </span>
            </div>
          </div>

          <div className="tasks-actions">
            {statuses.map((status) => (
              <button
                key={status}
                type="button"
                onClick={() => updateStatus(status)}
                className={task.status === status ? "active" : ""}
              >
                {status}
              </button>
            ))}
          </div>

          <div className="tasks-block">
            <h3>Description</h3>
            <p>{task.description || "No description provided."}</p>
          </div>

          <div className="tasks-block">
            <h3>Assigned Agent</h3>
            <p>{task.assigned_agent || "Unassigned"}</p>
          </div>

          <div className="tasks-block">
            <h3>Priority</h3>
            <p>{task.priority || "Medium"}</p>
          </div>

          <div className="tasks-block">
            <h3>Timeline</h3>
            <p>Created: {task.created_at || "—"}</p>
            <p>Completed: {task.completed_at || "Open"}</p>
          </div>

          {task.security_status && task.security_status !== "Pending" && (
            <div className="tasks-block">
              <h3>Security Review</h3>
              <div>
                <span
                  className="ui-status-pill"
                  style={{
                    background: (SECURITY_COLORS[task.security_status] || DEFAULT_SECURITY_STYLE).bg,
                    color: (SECURITY_COLORS[task.security_status] || DEFAULT_SECURITY_STYLE).color,
                    display: "inline-flex"
                  }}
                >
                  <span className="dot" aria-hidden="true" style={{ background: (SECURITY_COLORS[task.security_status] || DEFAULT_SECURITY_STYLE).color }}></span>
                  {task.security_status}
                </span>
              </div>
              {task.status === "Failed" && task.security_status === "Approved" && (
                <p style={{ color: "var(--status-danger)", marginTop: "var(--space-8)" }}>
                  ⚠ Invalid state: Failed tasks cannot be Approved
                </p>
              )}
              {task.security_notes && <p style={{ marginTop: "var(--space-8)" }}>{task.security_notes}</p>}
            </div>
          )}

          {task.output_files && task.output_files.length > 0 && (
            <div className="tasks-block">
              <h3>Output Files ({task.output_files.length})</h3>
              <div className="tasks-files">
                {task.output_files.map((file) => (
                  <div key={file} className="tasks-file-item">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                      <polyline points="14 2 14 8 20 8"></polyline>
                      <line x1="16" y1="13" x2="8" y2="13"></line>
                      <line x1="16" y1="17" x2="8" y2="17"></line>
                      <polyline points="10 9 9 9 8 9"></polyline>
                    </svg>
                    {file}
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
