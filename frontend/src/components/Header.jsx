const subtitles = {
  Dashboard: "Mission control overview for agents, workspaces, tasks, and runtime health.",
  Agents: "Manage local model workers before Qwen orchestration comes online.",
  Workspaces: "Track AI-generated projects, generated files, and collaboration timelines.",
  Tasks: "Follow delegated work from planning through build and security review.",
  Activity: "Search system events, build logs, agent messages, and security alerts.",
  Settings: "Configure runtime endpoints, models, appearance, and developer telemetry.",
};

export default function Header({ title, systemStatus }) {
  const statusText = systemStatus
    ? `${systemStatus.active_connections} connections`
    : "Connecting";

  return (
    <header className="header">
      <div>
        <p className="eyebrow">Command Center</p>
        <h1>{title}</h1>
        <p>{subtitles[title]}</p>
      </div>

      <div className="header-status">
        <span className="pulse-dot" />
        <span>{statusText}</span>
      </div>
    </header>
  );
}
