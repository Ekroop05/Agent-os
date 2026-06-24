import React from 'react';
import './ui.css';

export function ProgressBar({ progress = 0, className = '', ariaLabel = "Progress", ...props }) {
  const safeProgress = Math.min(Math.max(progress, 0), 100);
  
  return (
    <div 
      className={`ui-progress-container ${className}`} 
      role="progressbar" 
      aria-valuenow={safeProgress} 
      aria-valuemin="0" 
      aria-valuemax="100"
      aria-label={ariaLabel}
      {...props}
    >
      <div 
        className="ui-progress-bar" 
        style={{ width: `${safeProgress}%` }}
      ></div>
    </div>
  );
}
