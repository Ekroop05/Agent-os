import { useEffect, useState } from "react";
import { api } from "../../services/api";
import "./sprint5.css";

export default function EditTimeline({ workspaceId }) {
  const [timeline, setTimeline] = useState([]);

  useEffect(() => {
    if (!workspaceId) return;
    api.getProjectContext(workspaceId)
      .then((ctx) => {
        if (ctx && ctx.edit_timeline) {
          setTimeline(ctx.edit_timeline);
        } else {
          setTimeline([]);
        }
      })
      .catch(() => setTimeline([]));
  }, [workspaceId]);

  if (!timeline || timeline.length === 0) return null;

  return (
    <div className="bc-stagger-6" style={{ marginTop: 'var(--space-24)' }}>
      <div className="bc-hero-header" style={{ marginBottom: 'var(--space-16)' }}>
        <h3 style={{ margin: 0 }}>Edit Timeline</h3>
        <span className="wi-section-badge">{timeline.length} Events</span>
      </div>
      
      <div className="et-container">
        {timeline.map((evt, idx) => (
          <div className="et-item" key={idx}>
            <div className="et-rail">
              <div className="et-dot"></div>
              <div className="et-line"></div>
            </div>
            <div className="et-content">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="et-title">{evt.event}</span>
                <span className="et-time">{new Date(evt.timestamp).toLocaleTimeString()}</span>
              </div>
              {evt.details && <div className="et-details">{evt.details}</div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
