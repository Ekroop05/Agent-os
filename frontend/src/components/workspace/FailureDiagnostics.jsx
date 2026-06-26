import './workspace-intelligence.css';

/**
 * FailureDiagnostics — Feature 9
 * Displays failed tasks with failure time, assigned agent, affected files,
 * error context, and suggested actions. Does NOT generate fake diagnostics.
 */
export default function FailureDiagnostics({ tasks, activity }) {
  const failedTasks = tasks.filter((t) => t.status === 'Failed');

  if (failedTasks.length === 0) {
    return null; // Don't render if no failures
  }

  // Match activity errors to failed tasks for context
  const errorEvents = (activity || []).filter((e) => e.severity === 'error');

  return (
    <div className="wi-section" style={{ borderColor: 'rgba(248, 113, 113, 0.2)' }}>
      <div className="wi-section-header">
        <h3 className="wi-section-title" style={{ color: 'var(--status-danger)' }}>
          ⚠ Failure Diagnostics
        </h3>
        <span className="wi-section-badge" style={{ color: 'var(--status-danger)' }}>
          {failedTasks.length} {failedTasks.length === 1 ? 'failure' : 'failures'}
        </span>
      </div>
      <div className="wi-diagnostics">
        {failedTasks.map((task) => {
          // Find related error events
          const relatedErrors = errorEvents.filter(
            (e) => (e.message || '').includes(task.title || '') ||
                   (e.message || '').includes(task.id || '')
          );

          // Determine suggested action based on available info
          const suggestion = getSuggestion(task, relatedErrors);

          return (
            <div className="wi-diag-card" key={task.id}>
              <div className="wi-diag-header">
                <h4 className="wi-diag-title">{task.title || 'Untitled Task'}</h4>
                <span className="wi-diag-time">{task.completed_at || task.created_at || '—'}</span>
              </div>

              <div className="wi-diag-row">
                <span className="wi-diag-label">Assigned Agent</span>
                <span className="wi-diag-value">{task.assigned_agent || 'Unassigned'}</span>
              </div>

              <div className="wi-diag-row">
                <span className="wi-diag-label">Priority</span>
                <span className="wi-diag-value">{task.priority || 'Medium'}</span>
              </div>

              {task.description && (
                <div className="wi-diag-row">
                  <span className="wi-diag-label">Task Description</span>
                  <span className="wi-diag-value">{task.description}</span>
                </div>
              )}

              {task.security_notes && (
                <div className="wi-diag-row">
                  <span className="wi-diag-label">Security Notes</span>
                  <span className="wi-diag-value">{task.security_notes}</span>
                </div>
              )}

              {task.output_files && task.output_files.length > 0 && (
                <div className="wi-diag-row">
                  <span className="wi-diag-label">Affected Files</span>
                  <div className="wi-diag-files">
                    {task.output_files.map((f) => (
                      <span className="wi-diag-file" key={f}>{f}</span>
                    ))}
                  </div>
                </div>
              )}

              {relatedErrors.length > 0 && (
                <div className="wi-diag-row">
                  <span className="wi-diag-label">Error Context</span>
                  {relatedErrors.slice(0, 3).map((e, i) => (
                    <span className="wi-diag-value" key={i} style={{ color: 'var(--status-danger)' }}>
                      {e.message}
                    </span>
                  ))}
                </div>
              )}

              <div className="wi-diag-suggestion">
                <span>💡</span>
                {suggestion}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function getSuggestion(task, errors) {
  if (task.security_status === 'Rejected') {
    return 'This task was rejected by security review. Check security notes and update the implementation to address the identified concerns.';
  }
  if (errors.length > 0) {
    return 'Review the error context above and retry the task. If the error persists, check the agent logs for additional details.';
  }
  if (task.assigned_agent) {
    return `Retry this task or reassign to a different agent. The ${task.assigned_agent} agent may need updated configuration.`;
  }
  return 'Review the task description and retry. Ensure all dependencies are met before re-running.';
}
