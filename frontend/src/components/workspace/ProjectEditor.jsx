import { useState } from "react";
import { api } from "../../services/api";
import "./sprint5.css";

export default function ProjectEditor({ onCreateWorkspace }) {
  const [path, setPath] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAnalyze = async () => {
    if (!path.trim()) return;
    setLoading(true);
    setError(null);
    setAnalysis(null);
    try {
      const data = await api.analyzeProject(path.trim());
      setAnalysis(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleOpen = () => {
    if (analysis && onCreateWorkspace) {
      onCreateWorkspace({
        name: analysis.project_name,
        description: `Imported ${analysis.framework} project`,
        path: analysis.project_path,
        active_agents: 1,
      }, analysis);
    }
  };

  return (
    <div className="pe-card bc-stagger-1">
      <div className="bc-hero-header">
        <h3 style={{ margin: 0 }}>Open Existing Project</h3>
      </div>
      
      <div className="pe-input-group">
        <input 
          type="text" 
          placeholder="Absolute path to existing project folder..." 
          value={path}
          onChange={(e) => setPath(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
        />
        <button className="pe-btn" onClick={handleAnalyze} disabled={loading || !path.trim()}>
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </div>

      {error && <div style={{ color: "var(--status-error)", fontSize: "var(--text-sm)" }}>Error: {error}</div>}

      {analysis && (
        <div className="pe-analysis-grid">
          <div className="pe-stat-card">
            <span className="pe-stat-label">Framework</span>
            <span className="pe-stat-value">{analysis.framework}</span>
          </div>
          <div className="pe-stat-card">
            <span className="pe-stat-label">Total Files</span>
            <span className="pe-stat-value">{analysis.total_files}</span>
          </div>
          <div className="pe-stat-card">
            <span className="pe-stat-label">Components</span>
            <span className="pe-stat-value">{analysis.component_count}</span>
          </div>
          <div className="pe-stat-card">
            <span className="pe-stat-label">Pages/Routes</span>
            <span className="pe-stat-value">{analysis.page_count + analysis.route_count}</span>
          </div>
          <div className="pe-stat-card">
            <span className="pe-stat-label">Complexity</span>
            <span className="pe-stat-value" style={{ 
              color: analysis.risk_assessment.complexity === 'High' ? 'var(--status-error)' : 
                     analysis.risk_assessment.complexity === 'Medium' ? 'var(--status-warning)' : 
                     'var(--status-success)' 
            }}>
              {analysis.risk_assessment.complexity}
            </span>
          </div>
        </div>
      )}

      {analysis && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 'var(--space-8)' }}>
          <button className="bc-hero-btn bc-hero-btn-primary" onClick={handleOpen}>
            Open in Agent OS
          </button>
        </div>
      )}
    </div>
  );
}
