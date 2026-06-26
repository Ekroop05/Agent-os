import './workspace-intelligence.css';

/**
 * BuildTimeline — Feature 2
 * Visual timeline of build events with staggered fade-in.
 * Derives events from activity + buildEvents filtered by workspace context.
 */
export default function BuildTimeline({ activity, buildEvents, workspaceId }) {
  // Merge workspace-related activity and build events into a single timeline
  const workspaceActivity = (activity || []).filter(
    (e) => e && (
      (e.type || '').startsWith('WORKSPACE_') ||
      (e.type || '').startsWith('TASK_') ||
      (e.type || '').startsWith('BUILD_') ||
      (e.source || '').includes('Workspace') ||
      (e.source || '').includes('Builder') ||
      (e.source || '').includes('Architect') ||
      (e.source || '').includes('Security')
    )
  );

  const buildEvts = (buildEvents || []).map((e) => ({
    id: e.id || `build-${Math.random()}`,
    message: e.message || e.event_type || 'Build event',
    timestamp: e.timestamp || '',
    source: e.source || 'Build',
    severity: e.severity || 'info',
    type: e.event_type || 'BUILD',
  }));

  // Combine, deduplicate by id, sort newest first, limit to 20
  const seen = new Set();
  const merged = [...buildEvts, ...workspaceActivity]
    .filter((e) => {
      if (!e || !e.id || seen.has(e.id)) return false;
      seen.add(e.id);
      return true;
    })
    .slice(0, 20);

  if (merged.length === 0) {
    return (
      <div className="wi-section">
        <div className="wi-section-header">
          <h3 className="wi-section-title">Build Timeline</h3>
        </div>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)' }}>
          No build events yet. Start a build to see the timeline.
        </p>
      </div>
    );
  }

  return (
    <div className="wi-section">
      <div className="wi-section-header">
        <h3 className="wi-section-title">Build Timeline</h3>
        <span className="wi-section-badge">{merged.length} events</span>
      </div>
      <div className="wi-timeline">
        {merged.map((event, idx) => {
          const severity = event.severity || 'info';
          const isLast = idx === merged.length - 1;
          return (
            <div className="wi-timeline-event" key={event.id}>
              <div className="wi-timeline-rail">
                <div className={`wi-timeline-dot ${severity}`} />
                {!isLast && <div className="wi-timeline-line" />}
              </div>
              <div className="wi-timeline-body">
                <p className="wi-timeline-msg">{event.message}</p>
                <div className="wi-timeline-meta">
                  <span>{event.source || '—'}</span>
                  <span>{event.timestamp || 'Just now'}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
