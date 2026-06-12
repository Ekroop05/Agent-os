import { useState } from "react";
import { api } from "../services/api";

const statuses = ["Pending", "Running", "Reviewing", "Blocked", "Completed"];

export default function Tasks({ data, setData }) {
  const [selectedTaskId, setSelectedTaskId] = useState(data.tasks[0]?.id);
  const [draft, setDraft] = useState({
    title: "",
    description: "",
    assigned_agent: "Head Agent",
    priority: "Medium",
  });
  const effectiveTaskId = selectedTaskId || data.tasks[0]?.id;
  const task = data.tasks.find((item) => item.id === effectiveTaskId) || data.tasks[0];

  async function createTask(event) {
    event.preventDefault();
    const created = await api.createTask(draft);
    setData((current) => ({ ...current, tasks: [created, ...current.tasks] }));
    setSelectedTaskId(created.id);
    setDraft({ title: "", description: "", assigned_agent: "Head Agent", priority: "Medium" });
  }

  async function updateStatus(status) {
    const updated = await api.updateTask({ id: task.id, status });
    setData((current) => ({
      ...current,
      tasks: current.tasks.map((item) => (item.id === updated.id ? updated : item)),
    }));
  }

  return (
    <div className="split-page">
      <section className="table-panel">
        <div className="section-heading">
          <h2>Delegated Tasks</h2>
          <span>{data.tasks.length} tracked</span>
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
            {data.agents.map((agent) => (
              <option key={agent.id} value={agent.name}>{agent.name}</option>
            ))}
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
            <span>Created</span>
            <span>Completed</span>
          </div>
          {data.tasks.map((item) => (
            <button
              className="task-table-row"
              key={item.id}
              type="button"
              onClick={() => setSelectedTaskId(item.id)}
            >
              <span>{item.title}</span>
              <span>{item.assigned_agent}</span>
              <span>{item.priority}</span>
              <span className={`status-pill ${item.status.toLowerCase()}`}>{item.status}</span>
              <span>{item.created_at}</span>
              <span>{item.completed_at || "Open"}</span>
            </button>
          ))}
        </div>
      </section>

      {task && (
        <section className="detail-panel">
          <div className="section-heading">
            <h2>{task.title}</h2>
            <span>{task.status}</span>
          </div>
          <div className="agent-actions">
            {statuses.map((status) => (
              <button key={status} type="button" onClick={() => updateStatus(status)}>
                {status}
              </button>
            ))}
          </div>
          <Detail title="Description" items={[task.description]} />
          <Detail title="Assigned Agent" items={[task.assigned_agent]} />
          <Detail title="Priority" items={[task.priority]} />
          <Detail title="Created" items={[task.created_at]} />
          <Detail title="Completed" items={[task.completed_at || "Open"]} />
        </section>
      )}
    </div>
  );
}

function Detail({ title, items }) {
  return (
    <div className="detail-block">
      <h3>{title}</h3>
      {items.map((item) => (
        <p key={item}>{item}</p>
      ))}
    </div>
  );
}
