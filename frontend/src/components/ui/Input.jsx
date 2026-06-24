import React, { forwardRef } from 'react';
import './ui.css';

export const Input = forwardRef(({ label, id, className = '', containerClassName = '', ...props }, ref) => {
  return (
    <div className={`ui-input-container ${containerClassName}`}>
      {label && <label htmlFor={id} className="ui-input-label">{label}</label>}
      <input 
        id={id}
        ref={ref}
        className={`ui-input ${className}`}
        {...props}
      />
    </div>
  );
});

Input.displayName = 'Input';
