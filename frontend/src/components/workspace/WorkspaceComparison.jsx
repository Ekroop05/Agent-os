import "./sprint5.css";

export default function WorkspaceComparison({ comparison }) {
  if (!comparison) return null;

  return (
    <div className="bc-stagger-5" style={{ padding: 'var(--space-16)', background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-subtle)' }}>
      <div className="bc-hero-header" style={{ marginBottom: 'var(--space-16)' }}>
        <h3 style={{ margin: 0 }}>Snapshot Comparison</h3>
        <span className="wi-section-badge">{comparison.total_changes} Changes</span>
      </div>

      <div className="wc-grid">
        <div className="wc-col">
          <div className="wc-header">Added & Modified ({comparison.added_count + comparison.modified_count})</div>
          <div className="cp-file-list" style={{ maxHeight: '200px' }}>
            {comparison.files_added?.map((f) => (
              <div className="cp-file-item create" key={`a-${f}`} style={{ padding: '4px 8px' }}>
                <span style={{ opacity: 0.5 }}>+</span> {f}
              </div>
            ))}
            {comparison.files_modified?.map((f) => (
              <div className="cp-file-item modify" key={`m-${f}`} style={{ padding: '4px 8px' }}>
                <span style={{ opacity: 0.5 }}>~</span> {f}
              </div>
            ))}
          </div>
        </div>
        
        <div className="wc-col">
          <div className="wc-header">Removed ({comparison.removed_count})</div>
          <div className="cp-file-list" style={{ maxHeight: '200px' }}>
            {comparison.files_removed?.map((f) => (
              <div className="cp-file-item delete" key={`d-${f}`} style={{ padding: '4px 8px' }}>
                <span style={{ opacity: 0.5 }}>-</span> {f}
              </div>
            ))}
            {comparison.files_removed?.length === 0 && (
              <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-tertiary)', fontStyle: 'italic', padding: 'var(--space-8)' }}>
                No files removed.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
