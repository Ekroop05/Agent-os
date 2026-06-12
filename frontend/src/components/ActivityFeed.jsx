export default function ActivityFeed({ logs, limit }) {
  const visibleLogs = limit ? logs.slice(0, limit) : logs;

  return (
    <section className="panel scroll-panel">
      <div className="section-heading">
        <h2>Recent Activity</h2>
        <span>{visibleLogs.length} events</span>
      </div>

      <div className="activity-list">
        {visibleLogs.map((log) => (
          <div key={log.id} className="activity-item">
            <span className={`activity-dot ${log.type}`} />
            <div>
              <p>{log.message}</p>
              <small>
                {log.timestamp} / {log.source} / {log.severity}
              </small>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
