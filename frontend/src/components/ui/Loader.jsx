import React from 'react';
import './ui.css';

export function Loader({ size = 24, className = '', ...props }) {
  return (
    <div 
      className={`ui-loader ${className}`} 
      style={{ width: size, height: size }}
      role="status"
      aria-label="Loading"
      {...props}
    >
      <span className="sr-only" style={{ display: 'none' }}>Loading...</span>
    </div>
  );
}
