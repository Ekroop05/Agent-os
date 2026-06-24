import React from 'react';
import './Skeleton.css';

export function SkeletonLine({ width = '100%', height = '14px', className = '' }) {
  return (
    <div
      className={`ui-skeleton-wrapper ui-skeleton-line ${className}`}
      style={{ width, height }}
      aria-hidden="true"
    />
  );
}

export function SkeletonCard({ className = '' }) {
  return (
    <div className={`ui-skeleton-card ${className}`} aria-hidden="true">
      <SkeletonLine width="60%" height="20px" />
      <SkeletonLine width="40%" height="12px" />
      <div style={{ marginTop: 'auto', paddingTop: '16px' }}>
        <SkeletonLine width="100%" height="8px" />
      </div>
    </div>
  );
}

export function SkeletonCircle({ size = '32px', className = '' }) {
  return (
    <div
      className={`ui-skeleton-wrapper ui-skeleton-circle ${className}`}
      style={{ width: size, height: size }}
      aria-hidden="true"
    />
  );
}

export function SkeletonList({ rows = 3, className = '' }) {
  return (
    <div className={`ui-skeleton-list ${className}`}>
      {Array.from({ length: rows }).map((_, idx) => (
        <div key={idx} style={{ display: 'flex', gap: '12px', marginBottom: '12px' }}>
          <SkeletonCircle size="24px" />
          <div style={{ flex: 1 }}>
            <SkeletonLine width="80%" height="12px" />
            <SkeletonLine width="40%" height="10px" />
          </div>
        </div>
      ))}
    </div>
  );
}
