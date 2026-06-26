import './workspace-intelligence.css';

/**
 * WorkspaceHealth — Feature 3
 * Health card showing build health, task completion rate, files generated,
 * warnings, and errors — all computed from existing data.
 */
export default function WorkspaceHealth({ tasks, activity, workspace }) {
  const total = tasks.length;
  const completed = tasks.filter((t) => t.status === 'Completed').length;
  const failed = tasks.filter((t) => t.status === 'Failed').length;
  const running = tasks.filter((t) => ['Running', 'Reviewing'].includes(t.status)).length;
  const filesGenerated = tasks.reduce((acc, t) => acc + (t.output_files?.length || 0), 0);
  const completionRate = total > 0 ? Math.round((completed / total) * 100) : 0;

  // Derive warnings/errors from activity
  const warnings = (activity || []).filter((e) => e.severity === 'warning').slice(0, 5);
  const errors = (activity || []).filter((e) => e.severity === 'error').slice(0, 5);

  // Build health: composite score
  const healthScore = total > 0
    ? Math.round(((completed / total) * 70) + (failed === 0 ? 30 : Math.max(0, 30 - failed * 10)))
    : 100;

  return (
    <div className="wi-section">
      <div className="wi-section-header">
        <h3 className="wi-section-title">Workspace Health</h3>
        <span className="wi-section-badge" style={{
          color: healthScore >= 80 ? 'var(--status-success)' : healthScore >= 50 ? 'var(--status-warning)' : 'var(--status-danger)',
        }}>
          {healthScore}%
        </span>
      </div>

      <div className="wi-health">
        <HealthItem label="Build Health" value={`${healthScore}%`} percent={healthScore} />
        <HealthItem label="Completion" value={`${completionRate}%`} percent={completionRate} />
        <HealthItem label="Files Generated" value={filesGenerated} />
        <HealthItem label="Status" value={workspace?.status || 'Planning'} />
      </div>

      {(warnings.length > 0 || errors.length > 0) && (
        <div className="wi-health-warnings">
          {errors.map((e, i) => (
            <div className="wi-health-error-item" key={`err-${i}`}>
              <span>✗</span> {e.message}
            </div>
          ))}
          {warnings.map((e, i) => (
            <div className="wi-health-warning-item" key={`warn-${i}`}>
              <span>⚠</span> {e.message}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function HealthItem({ label, value, percent }) {
  return (
    <div className="wi-health-item">
      <div className="wi-health-label">
        <span className="wi-health-name">{label}</span>
        <span className="wi-health-val">{value}</span>
      </div>
      {percent !== undefined && (
        <div className="ui-progress-container">
          <div className="ui-progress-bar" style={{ width: `${percent}%` }} />
        </div>
      )}
    </div>
  );
}
