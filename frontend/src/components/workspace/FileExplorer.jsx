import { useState } from 'react';
import './workspace-intelligence.css';

/**
 * FileExplorer — Feature 4
 * In-app file tree browser. Parses output_files from tasks into a nested
 * directory structure with expand/collapse and agent attribution.
 */
export default function FileExplorer({ tasks }) {
  // Build file tree from task output_files
  const fileEntries = [];
  for (const task of tasks) {
    if (!task.output_files) continue;
    for (const file of task.output_files) {
      fileEntries.push({
        path: file,
        agent: task.assigned_agent || 'Unknown',
        status: task.status,
      });
    }
  }

  if (fileEntries.length === 0) {
    return (
      <div className="wi-section">
        <div className="wi-section-header">
          <h3 className="wi-section-title">File Explorer</h3>
        </div>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)' }}>
          No files generated yet.
        </p>
      </div>
    );
  }

  // Parse paths into tree structure
  const tree = buildTree(fileEntries);

  return (
    <div className="wi-section">
      <div className="wi-section-header">
        <h3 className="wi-section-title">File Explorer</h3>
        <span className="wi-section-badge">{fileEntries.length} files</span>
      </div>
      <div className="wi-explorer">
        {Object.entries(tree).map(([name, node]) => (
          <TreeNode key={name} name={name} node={node} />
        ))}
      </div>
    </div>
  );
}

function buildTree(entries) {
  const root = {};
  for (const entry of entries) {
    const parts = entry.path.replace(/\\/g, '/').split('/');
    let current = root;
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      if (i === parts.length - 1) {
        // File leaf
        if (!current.__files) current.__files = [];
        current.__files.push({ name: part, agent: entry.agent, path: entry.path });
      } else {
        // Directory
        if (!current[part]) current[part] = {};
        current = current[part];
      }
    }
  }
  return root;
}

function TreeNode({ name, node }) {
  const [open, setOpen] = useState(true);
  const files = node.__files || [];
  const subdirs = Object.entries(node).filter(([k]) => k !== '__files');
  const count = files.length + subdirs.reduce((a, [, v]) => a + countFiles(v), 0);

  if (files.length === 0 && subdirs.length === 0) return null;

  // If this is a pure file leaf (no subdirectories, just the files array)
  // render it as a directory with files inside
  return (
    <div className="wi-explorer-folder">
      <button className="wi-explorer-folder-header" onClick={() => setOpen(!open)}>
        <svg className={`wi-explorer-chevron ${open ? 'open' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="9 18 15 12 9 6" />
        </svg>
        <span className="wi-explorer-folder-name">{name}/</span>
        <span className="wi-explorer-folder-count">{count}</span>
      </button>
      {open && (
        <div className="wi-explorer-children">
          {subdirs.map(([subName, subNode]) => (
            <TreeNode key={subName} name={subName} node={subNode} />
          ))}
          {files.map((file) => (
            <div className="wi-explorer-file" key={file.path}>
              <svg className="wi-explorer-file-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              {file.name}
              <span className="wi-explorer-file-agent">{file.agent}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function countFiles(node) {
  let count = (node.__files || []).length;
  for (const [k, v] of Object.entries(node)) {
    if (k !== '__files') count += countFiles(v);
  }
  return count;
}
