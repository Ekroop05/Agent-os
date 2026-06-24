import { useState } from "react";
import AgentCard from "../components/AgentCard";
import { api } from "../services/api";

export default function Agents({ data, setData }) {
  const [selectedAgentId, setSelectedAgentId] = useState(data.agents[0]?.id);
  const effectiveAgentId = selectedAgentId || data.agents[0]?.id;
  const agent = data.agents.find((item) => item.id === effectiveAgentId) || data.agents[0];

  async function handleAction(action, agentId) {
    const updated = await api[`${action}Agent`](agentId);
    setData((current) => ({
      ...current,
      agents: current.agents.map((item) => (item.id === updated.id ? updated : item)),
    }));
  }

  return (
    <div className="split-page" style={{ animation: "fadeIn var(--transition-normal) ease-out" }}>
      <section className="agent-grid" style={{ gap: "var(--space-24)" }}>
        {data.agents.map((item, idx) => (
          <div key={item.id} style={{ animation: `slideUp 0.4s ease-out ${idx * 0.1}s both` }}>
            <AgentCard
              agent={item}
              onAction={handleAction}
              onSelect={(selected) => setSelectedAgentId(selected.id)}
            />
          </div>
        ))}
      </section>

      {agent && (
        <section className="dash-panel" style={{ animation: "slideUp 0.4s ease-out 0.2s both" }}>
          <div className="dash-panel-header" style={{ marginBottom: "var(--space-24)" }}>
            <h2 className="dash-panel-title" style={{ fontSize: "var(--text-xl)" }}>{agent.name} Details</h2>
            <span className="dash-panel-badge">{agent.uptime}</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-24)" }}>
            <DetailBlock title="Role" items={[agent.role]} />
            <DetailBlock title="Assigned Model" items={[agent.model]} />
            <DetailBlock title="Current Task" items={[agent.current_task]} />
            <DetailBlock title="Lifecycle State" items={[agent.status]} />
            <DetailBlock title="Memory Usage" items={[`${agent.memory_usage}%`]} />
          </div>
        </section>
      )}
    </div>
  );
}

function DetailBlock({ title, items }) {
  return (
    <div>
      <h3 style={{ margin: "0 0 var(--space-8)", fontSize: "var(--text-sm)", color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>{title}</h3>
      {items.map((item) => (
        <p key={item} style={{ margin: 0, color: "var(--text-secondary)", fontSize: "var(--text-md)" }}>{item}</p>
      ))}
    </div>
  );
}
