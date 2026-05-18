import React from 'react';

export interface EmptyStateProps {
  /** Optional icon node (e.g. Heroicon element) */
  icon?: React.ReactNode;
  /** Required title */
  title: string;
  /** Optional supporting description */
  description?: React.ReactNode;
  /** Optional action slot (button, link) */
  action?: React.ReactNode;
  /** Optional override classes */
  className?: string;
}

/**
 * Inline empty-state placeholder used inside cards.
 */
const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  className = '',
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center text-center py-8 px-4 ${className}`}
    >
      {icon && <div className="text-slate-400 mb-2 [&>svg]:h-8 [&>svg]:w-8">{icon}</div>}
      <p className="text-sm font-semibold text-slate-900">{title}</p>
      {description && (
        <p className="text-xs text-slate-500 mt-1 max-w-md">{description}</p>
      )}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
};

export default EmptyState;
