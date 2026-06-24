import React from 'react';
import './layout.css';

export function AppShell({ children, className = '' }) {
  return (
    <div className={`layout-app-shell ${className}`}>
      {children}
    </div>
  );
}
