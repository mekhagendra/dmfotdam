import React from 'react';

export interface PageHeaderProps {
  /** Page title */
  title: React.ReactNode;
  /** Optional subtitle / description */
  subtitle?: React.ReactNode;
  /** Right-aligned action slot (filters, buttons) */
  actions?: React.ReactNode;
  /** Optional override classes */
  className?: string;
}

/**
 * Standard page header. Sits at the top of every page with `mb-6` spacing.
 */
const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  actions,
  className = '',
}) => {
  return (
    <header
      className={`flex flex-col md:flex-row md:items-end md:justify-between gap-3 mb-6 ${className}`}
    >
      <div>
        <h1 className="text-2xl font-bold text-slate-900 leading-tight">{title}</h1>
        {subtitle && (
          <div className="text-sm text-slate-600 mt-1 flex items-center gap-3 flex-wrap">
            {subtitle}
          </div>
        )}
      </div>
      {actions && (
        <div className="flex items-center gap-2 flex-wrap">{actions}</div>
      )}
    </header>
  );
};

export default PageHeader;
