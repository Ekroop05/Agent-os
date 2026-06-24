import React from 'react';
import './ui.css';

export function Card({ children, hoverable = false, className = '', ...props }) {
  return (
    <div className={`ui-card ${hoverable ? 'ui-card-hoverable' : ''} ${className}`} {...props}>
      {children}
    </div>
  );
}

Card.Header = function CardHeader({ children, className = '', ...props }) {
  return <div className={`ui-card-header ${className}`} {...props}>{children}</div>;
};

Card.Body = function CardBody({ children, className = '', ...props }) {
  return <div className={`ui-card-body ${className}`} {...props}>{children}</div>;
};

Card.Footer = function CardFooter({ children, className = '', ...props }) {
  return <div className={`ui-card-footer ${className}`} {...props}>{children}</div>;
};
