import './workspace-intelligence.css';

/**
 * TaskGraph — Feature 6
 * CSS-only visual task pipeline showing Completed → Running → Pending stages.
 * Nodes are colored by status. Hover reveals task details.
 */
export default function TaskGraph({ tasks }) {
  const completed = tasks.filter((t) => t.status === 'Completed');
  const running = tasks.filter((t) => ['Running', 'Reviewing', 'Assigned'].includes(t.status));
  const pending = tasks.filter((t) => t.status === 'Pending');
  const failed = tasks.filter((t) => t.status === 'Failed');
  const blocked = tasks.filter((t) => t.status === 'Blocked');

  if (tasks.length === 0) {
    return (
      <div className="wi-section">
        <div className="wi-section-header">
          <h3 className="wi-section-title">Task Pipeline</h3>
        </div>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)' }}>
          No tasks to visualize.
        </p>
      </div>
    );
  }

  return (
    <div className="wi-section">
      <div className="wi-section-header">
        <h3 className="wi-section-title">Task Pipeline</h3>
        <span className="wi-section-badge">{tasks.length} tasks</span>
      </div>
      <div className="wi-graph">
        <div className="wi-graph-pipeline">
          <Stage title="Completed" count={completed.length} tasks={completed} status="completed" />
          <Connector />
          <Stage title="Running" count={running.length} tasks={running} status="running" />
          <Connector />
          <Stage title="Pending" count={pending.length} tasks={pending} status="pending" />
          {failed.length > 0 && (
            <>
              <Connector />
              <Stage title="Failed" count={failed.length} tasks={failed} status="failed" />
            </>
          )}
          {blocked.length > 0 && (
            <>
              <Connector />
              <Stage title="Blocked" count={blocked.length} tasks={blocked} status="pending" />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Stage({ title, count, tasks, status }) {
  return (
    <div className="wi-graph-stage">
      <div className="wi-graph-stage-header">
        <span className="wi-graph-stage-title">{title}</span>
        <span className="wi-graph-stage-count">{count}</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {tasks.slice(0, 8).map((task) => (
          <div className={`wi-graph-node ${status}`} key={task.id}>
            {task.title || 'Untitled'}
            <div className="wi-graph-node-tooltip">
              {task.title || 'Untitled'} — {task.assigned_agent || 'Unassigned'}
            </div>
          </div>
        ))}
        {tasks.length > 8 && (
          <div className="wi-graph-node" style={{ textAlign: 'center', color: 'var(--text-tertiary)' }}>
            +{tasks.length - 8} more
          </div>
        )}
      </div>
    </div>
  );
}

function Connector() {
  return (
    <div className="wi-graph-connector">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <polyline points="9 18 15 12 9 6" />
      </svg>
    </div>
  );
}
