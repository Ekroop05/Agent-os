import React from 'react';
import './ui.css';

export function Badge({ children, className = '', ...props }) {
  return (
    <span className={`ui-badge ${className}`} {...props}>
      {children}
    </span>
  );
}
