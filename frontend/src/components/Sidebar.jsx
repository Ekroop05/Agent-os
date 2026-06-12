const navItems = [
  { path: "/", label: "Dashboard", icon: "D" },
  { path: "/architect", label: "Architect", icon: "A" },
  { path: "/agents", label: "Agents", icon: "G" },
  { path: "/workspaces", label: "Workspaces", icon: "W" },
  { path: "/tasks", label: "Tasks", icon: "T" },
  { path: "/activity", label: "Activity", icon: "L" },
  { path: "/sandbox", label: "Sandbox", icon: "S" },
  { path: "/settings", label: "Settings", icon: "*" },
];

export default function Sidebar({ currentPath, onNavigate, visibilityMode, setVisibilityMode }) {
  return (
    <aside className="sidebar">
      <button className="brand" type="button" onClick={() => onNavigate("/")}>
        <span className="brand-mark">AOS</span>
        <span>
          <strong>Agent OS</strong>
          <small>Local multi-agent runtime</small>
        </span>
      </button>

      <nav className="sidebar-nav" aria-label="Primary">
        {navItems.map((item) => (
          <button
            key={item.path}
            className={currentPath === item.path ? "nav-item active" : "nav-item"}
            type="button"
            onClick={() => onNavigate(item.path)}
          >
            <span>{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>
    </aside>
  );
}
