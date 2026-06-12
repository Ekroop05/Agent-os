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
    <div className="split-page">
      <section className="agent-grid">
        {data.agents.map((item) => (
          <AgentCard
            key={item.id}
            agent={item}
            onAction={handleAction}
            onSelect={(selected) => setSelectedAgentId(selected.id)}
          />
        ))}
      </section>

      {agent && (
        <section className="detail-panel">
          <div className="section-heading">
            <h2>{agent.name} Details</h2>
            <span>{agent.uptime}</span>
          </div>

          <DetailBlock title="Role" items={[agent.role]} />
          <DetailBlock title="Assigned Model" items={[agent.model]} />
          <DetailBlock title="Current Task" items={[agent.current_task]} />
          <DetailBlock title="Lifecycle State" items={[agent.status]} />
          <DetailBlock title="Memory Usage" items={[`${agent.memory_usage}%`]} />
        </section>
      )}
    </div>
  );
}

function DetailBlock({ title, items }) {
  return (
    <div className="detail-block">
      <h3>{title}</h3>
      {items.map((item) => (
        <p key={item}>{item}</p>
      ))}
    </div>
  );
}
