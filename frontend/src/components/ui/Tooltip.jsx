import React from 'react';
import './ui.css';

export function Tooltip({ children, content, className = '', ...props }) {
  return (
    <div className={`ui-tooltip-container ${className}`} {...props}>
      {children}
      <div className="ui-tooltip-content" role="tooltip">
        {content}
      </div>
    </div>
  );
}
