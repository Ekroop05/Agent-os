import React from 'react';
import './ui.css';

export function Button({ 
  children, 
  variant = 'primary', 
  isLoading = false, 
  icon, 
  className = '', 
  disabled, 
  ...props 
}) {
  return (
    <button 
      className={`ui-button ui-button-${variant} ${className}`}
      disabled={isLoading || disabled}
      {...props}
    >
      {isLoading && <span className="ui-loader" style={{ width: 14, height: 14, borderWidth: 2 }}></span>}
      {!isLoading && icon && <span className="ui-button-icon">{icon}</span>}
      {children}
    </button>
  );
}
