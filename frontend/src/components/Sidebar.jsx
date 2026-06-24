import './Sidebar.css';

/* ── SVG Icon Components ─────────────────────────── */
const icons = {
  dashboard: (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  ),
  architect: (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2L2 7l10 5 10-5-10-5z" />
      <path d="M2 17l10 5 10-5" />
      <path d="M2 12l10 5 10-5" />
    </svg>
  ),
  agents: (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="4" />
      <path d="M20 21a8 8 0 10-16 0" />
    </svg>
  ),
  workspaces: (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
    </svg>
  ),
  tasks: (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 11l3 3L22 4" />
      <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" />
    </svg>
  ),
  activity: (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  ),
  sandbox: (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="16 18 22 12 16 6" />
      <polyline points="8 6 2 12 8 18" />
    </svg>
  ),
  settings: (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
    </svg>
  ),
};

const navItems = [
  { path: "/", label: "Dashboard", icon: "dashboard", section: "core" },
  { path: "/architect", label: "Architect", icon: "architect", section: "core" },
  { path: "/agents", label: "Agents", icon: "agents", section: "core" },
  { path: "/workspaces", label: "Workspaces", icon: "workspaces", section: "workspace" },
  { path: "/tasks", label: "Tasks", icon: "tasks", section: "workspace" },
  { path: "/activity", label: "Activity", icon: "activity", section: "workspace" },
  { path: "/sandbox", label: "Sandbox", icon: "sandbox", section: "tools" },
  { path: "/settings", label: "Settings", icon: "settings", section: "tools" },
];

const sections = {
  core: "Platform",
  workspace: "Operations",
  tools: "Tools",
};

export default function Sidebar({ currentPath, onNavigate, visibilityMode, setVisibilityMode }) {
  const grouped = {};
  navItems.forEach((item) => {
    if (!grouped[item.section]) grouped[item.section] = [];
    grouped[item.section].push(item);
  });

  return (
    <aside className="sidebar sidebar-v2">
      <button className="sidebar-v2-brand" type="button" onClick={() => onNavigate("/")} aria-label="Go to Dashboard">
        <span className="sidebar-v2-logo">AOS</span>
        <span className="sidebar-v2-brand-text">
          <strong>Agent OS</strong>
          <small>Multi-agent runtime</small>
        </span>
      </button>

      <nav className="sidebar-v2-nav" aria-label="Primary">
        {Object.entries(grouped).map(([sectionKey, items]) => (
          <div key={sectionKey}>
            <div className="sidebar-v2-section-label">{sections[sectionKey]}</div>
            {items.map((item) => (
              <button
                key={item.path}
                className={`sidebar-v2-item${currentPath === item.path ? " active" : ""}`}
                type="button"
                onClick={() => onNavigate(item.path)}
                aria-current={currentPath === item.path ? "page" : undefined}
              >
                {icons[item.icon]}
                {item.label}
              </button>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-v2-footer">
        <div className="sidebar-v2-version">
          <span className="sidebar-v2-version-dot" />
          v2.0 · Local Runtime
        </div>
      </div>
    </aside>
  );
}
