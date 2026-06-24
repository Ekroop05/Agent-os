import { useMemo, useState } from "react";
import "./Activity.css";

const types = ["all", "AGENT", "TASK", "WORKSPACE", "SYSTEM"];
const severities = ["all", "info", "warning", "error", "success"];
const pageSize = 8;

export default function Activity({ data, visibilityMode }) {
  const [query, setQuery] = useState("");
  const [type, setType] = useState("all");
  const [severity, setSeverity] = useState("all");
  const [page, setPage] = useState(1);

  const filtered = useMemo(
    () =>
      data.activity.filter((event) => {
        const haystack = `${event.message} ${event.source} ${event.type}`.toLowerCase();
        const matchesQuery = haystack.includes(query.toLowerCase());
        const matchesType = type === "all" || event.type.startsWith(type);
        const matchesSeverity = severity === "all" || event.severity === severity;
        
        let matchesVisibility = true;
        if (visibilityMode === "Executive") {
          matchesVisibility = !event.type.startsWith("FILE_") && !event.type.startsWith("COMMAND_") && !event.type.startsWith("GIT_");
        }
        
        return matchesQuery && matchesType && matchesSeverity && matchesVisibility;
      }),
    [data.activity, query, severity, type, visibilityMode],
  );
  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  const pageItems = filtered.slice((page - 1) * pageSize, page * pageSize);

  return (
    <div className="activity-v2">
      <section className="activity-panel">
        <div className="activity-toolbar">
          <input
            aria-label="Search activity"
            placeholder="Search activity"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setPage(1);
            }}
          />
          <select aria-label="Filter type" value={type} onChange={(event) => setType(event.target.value)}>
            {types.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
          <select aria-label="Filter severity" value={severity} onChange={(event) => setSeverity(event.target.value)}>
            {severities.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </div>

        <div className="activity-feed">
          {pageItems.map((event, idx) => (
            <article 
              className="activity-event" 
              key={event.id}
              style={{ animation: `slideUp 0.3s ease-out ${idx * 0.05}s both` }}
            >
              <div className={`activity-event-dot ${event.severity}`} aria-hidden="true" />
              <div className="activity-event-content">
                <h3 className="activity-event-message">{event.message}</h3>
                <p className="activity-event-meta">
                  {event.timestamp} / <span>{event.source}</span> / {event.type}
                </p>
              </div>
            </article>
          ))}
        </div>

        <div className="activity-pager">
          <button type="button" disabled={page === 1} onClick={() => setPage((value) => value - 1)}>
            Previous
          </button>
          <span>Page {page} of {pageCount}</span>
          <button type="button" disabled={page === pageCount} onClick={() => setPage((value) => value + 1)}>
            Next
          </button>
        </div>
      </section>
    </div>
  );
}
