import { useState } from "react";

const AGENT_STATUS_STYLES = {
  Running: { color: "#86efac", glow: "rgba(34, 197, 94, 0.4)", icon: "●", label: "Running" },
  Thinking: { color: "#7dd3fc", glow: "rgba(56, 189, 248, 0.4)", icon: "●", label: "Thinking" },
  Reviewing: { color: "#fde68a", glow: "rgba(245, 158, 11, 0.4)", icon: "●", label: "Reviewing" },
  Paused: { color: "#f9a8d4", glow: "rgba(236, 72, 153, 0.3)", icon: "●", label: "Paused" },
  Idle: { color: "#64748b", glow: "none", icon: "○", label: "Idle" },
  Error: { color: "#fca5a5", glow: "rgba(248, 113, 113, 0.4)", icon: "●", label: "Error" },
};

const JOB_STATUS_ICON = {
  Running: { icon: "▶", color: "#c4b5fd" },
  Pending: { icon: "◎", color: "#7dd3fc" },
  Completed: { icon: "✓", color: "#86efac" },
  Failed: { icon: "✗", color: "#fca5a5" },
  Cancelled: { icon: "⊘", color: "#94a3b8" },
};

/**
 * Global Agent Status Bar — Sprint 4.5
 *
 * Visible on every page. Shows:
 * - Agent status indicators (Running/Thinking/Idle/etc.)
 * - Active job count with current task names
 * - Collapsible event timeline
 *
 * Props:
 *   agents: Agent[]
 *   jobs: Job[]
 *   timeline: TimelineEvent[]
 */
export default function AgentStatusBar({ agents = [], jobs = [], timeline = [] }) {
  const [expanded, setExpanded] = useState(false);

  const activeJobs = jobs.filter((j) => j.status === "Running" || j.status === "Pending");
  const hasActivity = agents.some((a) => a.status === "Running") || activeJobs.length > 0;

  return (
    <div className={`agent-status-bar ${expanded ? "expanded" : ""}`}>
      {/* ── Main Bar ──────────────────────── */}
      <div className="status-bar-main" onClick={() => setExpanded(!expanded)}>
        <div className="status-bar-agents">
          {agents.map((agent) => {
            const style = AGENT_STATUS_STYLES[agent.status] || AGENT_STATUS_STYLES.Idle;
            return (
              <div className="status-bar-agent" key={agent.id} title={`${agent.name}: ${agent.current_task}`}>
                <span
                  className={`status-dot ${agent.status === "Running" ? "pulse" : ""}`}
                  style={{ color: style.color, textShadow: `0 0 8px ${style.glow}` }}
                >
                  {style.icon}
                </span>
                <span className="status-agent-name">{agent.name?.replace(" Agent", "")}</span>
                <span className="status-agent-state" style={{ color: style.color }}>
                  {agent.status === "Running" ? agent.current_task?.slice(0, 30) || style.label : style.label}
                </span>
              </div>
            );
          })}
        </div>

        <div className="status-bar-jobs">
          {activeJobs.length > 0 && (
            <span className="status-job-count">
              <span className="status-dot pulse" style={{ color: "#c4b5fd" }}>●</span>
              {activeJobs.length} active job{activeJobs.length !== 1 ? "s" : ""}
            </span>
          )}
          {!hasActivity && (
            <span className="status-idle-label">All agents idle</span>
          )}
        </div>

        <button
          className="status-bar-toggle"
          type="button"
          onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
          title={expanded ? "Collapse timeline" : "Expand timeline"}
        >
          {expanded ? "▼" : "▲"} Timeline
        </button>
      </div>

      {/* ── Expanded Timeline ─────────────── */}
      {expanded && (
        <div className="status-bar-timeline">
          <div className="timeline-header">
            <h4>Agent Event Timeline</h4>
            <span className="timeline-count">{timeline.length} events</span>
          </div>
          <div className="timeline-list">
            {timeline.length === 0 ? (
              <div className="timeline-empty">No events yet. Start a build to see activity here.</div>
            ) : (
              timeline.slice(0, 30).map((event, idx) => (
                <div className="timeline-item" key={event.id || idx}>
                  <span className={`timeline-dot severity-${event.severity || "info"}`} />
                  <span className="timeline-source">{event.source}</span>
                  <span className="timeline-message">{event.message}</span>
                  <span className="timeline-time">{event.timestamp?.split(" ")[1] || ""}</span>
                </div>
              ))
            )}
          </div>

          {/* Active Jobs Detail */}
          {jobs.length > 0 && (
            <div className="timeline-jobs">
              <h4>Jobs</h4>
              {jobs.slice(0, 10).map((job) => {
                const style = JOB_STATUS_ICON[job.status] || JOB_STATUS_ICON.Pending;
                return (
                  <div className="timeline-job-row" key={job.job_id}>
                    <span style={{ color: style.color }}>{style.icon}</span>
                    <span className="timeline-job-agent">{job.agent}</span>
                    <span className="timeline-job-message">{job.message?.slice(0, 40)}</span>
                    <div className="timeline-job-progress">
                      <div
                        className="timeline-job-fill"
                        style={{ width: `${job.progress || 0}%`, background: style.color }}
                      />
                    </div>
                    <span className="timeline-job-percent">{job.progress || 0}%</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
