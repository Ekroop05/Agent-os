import React from 'react';
import './layout.css';

export function Topbar({ left, center, right, className = '' }) {
  return (
    <header className={`layout-topbar ${className}`}>
      <div className="layout-topbar-left">{left}</div>
      <div className="layout-topbar-center">{center}</div>
      <div className="layout-topbar-right">{right}</div>
    </header>
  );
}
