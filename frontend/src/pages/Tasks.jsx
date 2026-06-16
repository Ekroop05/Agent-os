import { useState } from "react";
import { api } from "../services/api";

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
  // Filter to only valid task objects before any rendering
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
    <div className="split-page">
      <section className="table-panel">
        <div className="section-heading">
          <h2>Delegated Tasks</h2>
          <span>{validTasks.length} tracked</span>
        </div>

        <form className="inline-form" onSubmit={createTask}>
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

        <div className="task-table">
          <div className="task-table-head">
            <span>Task</span>
            <span>Agent</span>
            <span>Priority</span>
            <span>Status</span>
            <span>Security</span>
            <span>Created</span>
          </div>
          {validTasks.map((item) => {
            const itemStatus = item.status || "Pending";
            const securityStatus = item.security_status || "Pending";
            const secStyle = SECURITY_COLORS[securityStatus] || DEFAULT_SECURITY_STYLE;
            return (
              <button
                className={`task-table-row ${item.id === effectiveTaskId ? "selected" : ""}`}
                key={item.id}
                type="button"
                onClick={() => setSelectedTaskId(item.id)}
              >
                <span>{item.title || "Untitled"}</span>
                <span className="task-agent-name">{item.assigned_agent || "—"}</span>
                <span>{item.priority || "Medium"}</span>
                <span className={`status-pill ${itemStatus.toLowerCase()}`}>
                  {STATUS_ICONS[itemStatus] || "○"} {itemStatus}
                </span>
                <span>
                  {securityStatus !== "Pending" && (
                    <span
                      className="security-badge-inline"
                      style={{ background: secStyle.bg, color: secStyle.color }}
                    >
                      {securityStatus}
                    </span>
                  )}
                </span>
                <span>{item.created_at || "—"}</span>
              </button>
            );
          })}
        </div>
      </section>

      {task && (
        <section className="detail-panel">
          <div className="section-heading">
            <h2>{task.title || "Untitled"}</h2>
            <span className={`status-pill ${(task.status || "pending").toLowerCase()}`}>
              {STATUS_ICONS[task.status] || "○"} {task.status || "Pending"}
            </span>
          </div>
          <div className="agent-actions">
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
          <Detail title="Description" items={[task.description || "No description"]} />
          <Detail title="Assigned Agent" items={[task.assigned_agent || "Unassigned"]} />
          <Detail title="Priority" items={[task.priority || "Medium"]} />
          <Detail title="Created" items={[task.created_at || "—"]} />
          <Detail title="Completed" items={[task.completed_at || "Open"]} />

          {/* Security Review Info */}
          {task.security_status && task.security_status !== "Pending" && (
            <div className="detail-block">
              <h3>Security Review</h3>
              <p>
                <span
                  className="security-badge-inline"
                  style={{
                    background: (SECURITY_COLORS[task.security_status] || DEFAULT_SECURITY_STYLE).bg,
                    color: (SECURITY_COLORS[task.security_status] || DEFAULT_SECURITY_STYLE).color,
                  }}
                >
                  {task.security_status}
                </span>
              </p>
              {/* P5: Show warning for impossible states */}
              {task.status === "Failed" && task.security_status === "Approved" && (
                <p className="security-notes" style={{ color: "#fca5a5" }}>
                  ⚠ Invalid state: Failed tasks cannot be Approved
                </p>
              )}
              {task.security_notes && <p className="security-notes">{task.security_notes}</p>}
            </div>
          )}

          {/* Output Files */}
          {task.output_files && task.output_files.length > 0 && (
            <div className="detail-block">
              <h3>Output Files ({task.output_files.length})</h3>
              <div className="output-files-list">
                {task.output_files.map((file) => (
                  <p key={file} className="output-file-path">{file}</p>
                ))}
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

function Detail({ title, items }) {
  return (
    <div className="detail-block">
      <h3>{title}</h3>
      {(items || []).map((item) => (
        <p key={item || "empty"}>{item || "—"}</p>
      ))}
    </div>
  );
}
