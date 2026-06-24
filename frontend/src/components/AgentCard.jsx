import './AgentCard.css';

export default function AgentCard({ agent, compact = false, onSelect, onAction }) {
  const load = agent.status === "Running" ? Math.max(agent.memory_usage, 42) : agent.memory_usage;
  const statusClass = agent.status ? agent.status.toLowerCase() : "idle";

  return (
    <article className={`ac-card ${statusClass}`}>
      <div className="ac-header">
        <div>
          <h3 className="ac-title">{agent.name}</h3>
          <p className="ac-model">{agent.model}</p>
        </div>
        <span className={`ui-status-pill ${statusClass}`}>
          <span className="dot" aria-hidden="true"></span>
          {agent.status}
        </span>
      </div>

      <div className="ac-detail-row">
        <p className="ac-label">Role</p>
        <p className="ac-value">{agent.role}</p>
      </div>

      <div className="ac-detail-row">
        <p className="ac-label">Current Task</p>
        <p className="ac-value">{agent.current_task || "Waiting for instructions"}</p>
      </div>

      <div className="ac-meters">
        <div className="ac-meter">
          <div className="ac-meter-header">
            <span className="ac-meter-label">Runtime Load</span>
            <span className="ac-meter-val">{load}%</span>
          </div>
          <div className="ui-progress-container">
            <div className="ui-progress-bar" style={{ width: `${load}%` }} />
          </div>
        </div>
        <div className="ac-meter">
          <div className="ac-meter-header">
            <span className="ac-meter-label">Memory</span>
            <span className="ac-meter-val">{agent.memory_usage}%</span>
          </div>
          <div className="ui-progress-container">
            <div className="ui-progress-bar" style={{ width: `${agent.memory_usage}%` }} />
          </div>
        </div>
      </div>

      {!compact && (
        <div className="ac-actions">
          <button className="ac-btn" type="button" onClick={() => onAction?.("start", agent.id)}>Start</button>
          <button className="ac-btn" type="button" onClick={() => onAction?.("pause", agent.id)}>Pause</button>
          <button className="ac-btn" type="button" onClick={() => onAction?.("stop", agent.id)}>Stop</button>
          <button className="ac-btn" type="button" onClick={() => onSelect?.(agent)}>Open</button>
        </div>
      )}
    </article>
  );
}
