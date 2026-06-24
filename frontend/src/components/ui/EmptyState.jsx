import React from 'react';
import './ui.css';
import { Card } from './Card';

export function EmptyState({ title, description, icon, action, className = '' }) {
  return (
    <div className={`ui-empty-state ${className}`}>
      {icon && <div className="ui-empty-icon">{icon}</div>}
      <h3 className="text-h3" style={{ marginBottom: 'var(--space-8)' }}>{title}</h3>
      {description && <p className="text-body" style={{ marginBottom: 'var(--space-24)' }}>{description}</p>}
      {action && <div>{action}</div>}
    </div>
  );
}
