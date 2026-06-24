import './Header.css';

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
    <header className="header header-v2">
      <div className="header-v2-left">
        <span className="header-v2-breadcrumb">Agent OS</span>
        <span className="header-v2-sep">/</span>
        <h1 className="header-v2-title">{title}</h1>
      </div>

      <div className="header-v2-center">
        <div className="header-v2-search">
          <svg className="header-v2-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input type="text" placeholder="Search commands, tasks, workspaces..." aria-label="Search" />
          <span className="header-v2-shortcut">⌘K</span>
        </div>
      </div>

      <div className="header-v2-right">
        <div className="header-v2-status">
          <span className="header-v2-status-dot" />
          {statusText}
        </div>
        <div className="header-v2-avatar" title="User Profile">
          U
        </div>
      </div>
    </header>
  );
}
