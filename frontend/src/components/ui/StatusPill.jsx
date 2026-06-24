import React from 'react';
import './ui.css';

export function StatusPill({ status, label, className = '', ...props }) {
  const statusClass = status ? status.toLowerCase() : 'offline';
  
  return (
    <span className={`ui-status-pill ${statusClass} ${className}`} {...props}>
      <span className="dot" aria-hidden="true"></span>
      {label || status}
    </span>
  );
}
