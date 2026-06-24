import React from 'react';
import './layout.css';

export function ContentContainer({ children, constrainWidth = true, className = '' }) {
  return (
    <main className={`layout-content-container ${className}`}>
      {constrainWidth ? (
        <div className="layout-content-inner">
          {children}
        </div>
      ) : (
        children
      )}
    </main>
  );
}
