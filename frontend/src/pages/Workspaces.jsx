import { useState } from "react";
import { api } from "../services/api";

export default function Workspaces({ data, setData }) {
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState(data.workspaces[0]?.id);
  const [draft, setDraft] = useState({ name: "", description: "", active_agents: 1 });
  const effectiveWorkspaceId = selectedWorkspaceId || data.workspaces[0]?.id;
  const workspace = data.workspaces.find((item) => item.id === effectiveWorkspaceId) || data.workspaces[0];

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
  }

  const relatedTasks = data.tasks.filter((task) => task.status !== "Completed");
  const timeline = data.activity.filter((event) => event.type.startsWith("WORKSPACE_") || event.source.includes("Workspace"));

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
        {data.workspaces.map((item) => (
          <button
            className="workspace-card"
            key={item.id}
            type="button"
            onClick={() => setSelectedWorkspaceId(item.id)}
          >
            <span className="status-pill active">{item.status}</span>
            <h3>{item.name}</h3>
            <p>{item.active_agents} agents / {item.task_count} tasks</p>
            <p>{item.path}</p>
            <small>Created {item.created_at}</small>
          </button>
        ))}
      </section>

      {workspace && (
        <section className="detail-panel">
          <div className="section-heading">
            <h2>{workspace.name}</h2>
            <span>{workspace.status}</span>
          </div>
          <div className="agent-actions">
            <button type="button" onClick={() => setSelectedWorkspaceId(workspace.id)}>Open Workspace</button>
            <button type="button" onClick={() => deleteWorkspace(workspace.id)}>Delete Workspace</button>
          </div>

          <div className="detail-grid">
            <Detail title="Workspace Metadata" items={[workspace.description, workspace.path, `Created ${workspace.created_at}`]} />
            <Detail title="Active Agents" items={data.agents.filter((agent) => agent.status === "Running").map((agent) => agent.name)} />
            <Detail title="Assigned Tasks" items={relatedTasks.map((task) => task.title)} />
            <Detail title="Activity Timeline" items={timeline.length ? timeline.map((event) => event.message) : ["No workspace events yet"]} />
          </div>
        </section>
      )}
    </div>
  );
}

function Detail({ title, items }) {
  return (
    <div className="detail-block">
      <h3>{title}</h3>
      {items.length ? items.map((item) => <p key={item}>{item}</p>) : <p>None</p>}
    </div>
  );
}
