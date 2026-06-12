export default function AgentCard({ agent, compact = false, onSelect, onAction }) {
  const load = agent.status === "Running" ? Math.max(agent.memory_usage, 42) : agent.memory_usage;

  return (
    <article className="agent-card">
      <div className="card-heading">
        <div>
          <h3>{agent.name}</h3>
          <p>{agent.model}</p>
        </div>
        <span className={`status-pill ${agent.status.toLowerCase()}`}>{agent.status}</span>
      </div>

      <p className="card-label">Role</p>
      <p className="card-value">{agent.role}</p>

      <p className="card-label">Current Task</p>
      <p className="card-value">{agent.current_task}</p>

      <div className="meter-grid">
        <Meter label="Runtime Load" value={load} />
        <Meter label="Memory" value={agent.memory_usage} />
      </div>

      {!compact && (
        <div className="agent-actions">
          <button type="button" onClick={() => onAction?.("start", agent.id)}>Start</button>
          <button type="button" onClick={() => onAction?.("pause", agent.id)}>Pause</button>
          <button type="button" onClick={() => onAction?.("stop", agent.id)}>Stop</button>
          <button type="button" onClick={() => onAction?.("restart", agent.id)}>Restart</button>
          <button type="button" onClick={() => onSelect?.(agent)}>Open</button>
        </div>
      )}
    </article>
  );
}

function Meter({ label, value }) {
  return (
    <div className="meter">
      <div>
        <span>{label}</span>
        <strong>{value}%</strong>
      </div>
      <div className="meter-track">
        <span style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}
