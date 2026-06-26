import './workspace-intelligence.css';

/**
 * BuildMetrics — Feature 5
 * Premium analytics cards: Total/Completed/Pending/Running tasks,
 * files generated, workspace age, average task time.
 */
export default function BuildMetrics({ tasks, workspace }) {
  const total = tasks.length;
  const completed = tasks.filter((t) => t.status === 'Completed').length;
  const running = tasks.filter((t) => ['Running', 'Reviewing'].includes(t.status)).length;
  const pending = tasks.filter((t) => ['Pending', 'Assigned'].includes(t.status)).length;
  const failed = tasks.filter((t) => t.status === 'Failed').length;
  const filesGenerated = tasks.reduce((acc, t) => acc + (t.output_files?.length || 0), 0);

  // Workspace age
  let age = '—';
  if (workspace?.created_at) {
    try {
      const created = new Date(workspace.created_at);
      const now = new Date();
      const diffMs = now - created;
      const diffMins = Math.floor(diffMs / 60000);
      if (diffMins < 60) {
        age = `${diffMins}m`;
      } else if (diffMins < 1440) {
        age = `${Math.floor(diffMins / 60)}h ${diffMins % 60}m`;
      } else {
        age = `${Math.floor(diffMins / 1440)}d`;
      }
    } catch {
      age = '—';
    }
  }

  // Average task time
  let avgTime = '—';
  const completedWithTime = tasks.filter(
    (t) => t.status === 'Completed' && t.created_at && t.completed_at
  );
  if (completedWithTime.length > 0) {
    try {
      const totalMs = completedWithTime.reduce((acc, t) => {
        return acc + (new Date(t.completed_at) - new Date(t.created_at));
      }, 0);
      const avgMs = totalMs / completedWithTime.length;
      const avgSec = Math.round(avgMs / 1000);
      if (avgSec < 60) {
        avgTime = `${avgSec}s`;
      } else {
        avgTime = `${Math.floor(avgSec / 60)}m ${avgSec % 60}s`;
      }
    } catch {
      avgTime = '—';
    }
  }

  return (
    <div className="wi-metrics">
      <MetricCard label="Total Tasks" value={total} />
      <MetricCard label="Completed" value={completed} color="var(--status-success)" />
      <MetricCard label="Running" value={running} color="var(--color-primary)" />
      <MetricCard label="Pending" value={pending} />
      <MetricCard label="Failed" value={failed} color={failed > 0 ? 'var(--status-danger)' : undefined} />
      <MetricCard label="Files Generated" value={filesGenerated} color="var(--status-success)" />
      <MetricCard label="Workspace Age" value={age} />
      <MetricCard label="Avg Task Time" value={avgTime} />
    </div>
  );
}

function MetricCard({ label, value, color }) {
  return (
    <div className="wi-metric-card">
      <span className="wi-metric-val" style={color ? { color } : undefined}>{value}</span>
      <span className="wi-metric-label">{label}</span>
    </div>
  );
}
