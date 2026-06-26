import "./sprint5.css";

export default function ChangePreview({ preview }) {
  if (!preview) return null;

  return (
    <div className="cp-container bc-stagger-4">
      <div className="bc-hero-header">
        <h3 style={{ margin: 0 }}>Change Preview</h3>
        <span className={`cp-impact-badge ${preview.impact_level || 'low'}`}>
          Impact: {preview.impact_level || 'Low'}
        </span>
      </div>

      <div className="cp-file-list">
        {preview.files_to_create?.map((f) => (
          <div className="cp-file-item create" key={`c-${f}`}>
            <span style={{ opacity: 0.5 }}>+</span> {f}
          </div>
        ))}
        {preview.files_to_modify?.map((f) => (
          <div className="cp-file-item modify" key={`m-${f}`}>
            <span style={{ opacity: 0.5 }}>~</span> {f}
          </div>
        ))}
        {preview.files_to_delete?.map((f) => (
          <div className="cp-file-item delete" key={`d-${f}`}>
            <span style={{ opacity: 0.5 }}>-</span> {f}
          </div>
        ))}
      </div>

      {preview.affected_components?.length > 0 && (
        <div style={{ marginTop: 'var(--space-8)' }}>
          <div className="wi-section-header">
            <h4 style={{ margin: 0, fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>Affected Components</h4>
          </div>
          <div style={{ display: 'flex', gap: 'var(--space-8)', flexWrap: 'wrap' }}>
            {preview.affected_components.map((c) => (
              <span key={c} style={{ fontSize: 'var(--text-xs)', padding: '2px 8px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px' }}>
                {c}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
