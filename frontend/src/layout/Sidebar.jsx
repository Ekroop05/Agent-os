import React from 'react';
import './layout.css';

export function Sidebar({ header, children, footer, className = '' }) {
  return (
    <aside className={`layout-sidebar ${className}`}>
      {header && <div className="layout-sidebar-header">{header}</div>}
      <nav className="layout-sidebar-nav">
        {children}
      </nav>
      {footer && <div className="layout-sidebar-footer">{footer}</div>}
    </aside>
  );
}
