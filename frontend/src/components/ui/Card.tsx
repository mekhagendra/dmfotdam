import React from 'react';

const ACCENT_BAR: Record<string, string> = {
  blue: 'before:bg-[#3B82F6]',
  red: 'before:bg-[#EF4444]',
  amber: 'before:bg-[#F59E0B]',
  green: 'before:bg-[#10B981]',
  purple: 'before:bg-[#8B5CF6]',
};

export type CardAccent = 'blue' | 'red' | 'amber' | 'green' | 'purple';

export interface CardProps {
  /** Optional card title rendered in the header */
  title?: React.ReactNode;
  /** Optional secondary subtitle shown below the title */
  subtitle?: React.ReactNode;
  /** Right-aligned slot in the header (filters, links, buttons) */
  action?: React.ReactNode;
  /** Adds a 3px left accent bar of the given color */
  accent?: CardAccent;
  /** When true, renders a skeleton block in place of children */
  loading?: boolean;
  /** Additional class names appended to the card shell */
  className?: string;
  /** Padding override — defaults to p-5 */
  padding?: string;
  children?: React.ReactNode;
}

/**
 * Standard card shell — use everywhere instead of one-off markup.
 * `accent` adds a left 3px colored bar via a ::before pseudo-element.
 */
const Card: React.FC<CardProps> = ({
  title,
  subtitle,
  action,
  accent,
  loading,
  className = '',
  padding = 'p-5',
  children,
}) => {
  const accentClasses = accent
    ? `relative overflow-hidden before:content-[''] before:absolute before:inset-y-0 before:left-0 before:w-[3px] ${ACCENT_BAR[accent]}`
    : '';

  return (
    <section
      className={`bg-white rounded-lg border border-slate-200 shadow-sm ${padding} ${accentClasses} ${className}`}
    >
      {(title || action || subtitle) && (
        <header className="flex items-start justify-between mb-3 gap-3">
          <div>
            {title && (
              <h3 className="text-sm font-semibold text-slate-900 leading-tight">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>
            )}
          </div>
          {action && <div className="flex-shrink-0 text-xs text-slate-500">{action}</div>}
        </header>
      )}
      {loading ? (
        <div className="space-y-2" aria-busy="true" aria-label="Loading">
          <div className="h-3 bg-slate-200 rounded animate-pulse w-3/4" />
          <div className="h-3 bg-slate-200 rounded animate-pulse w-1/2" />
          <div className="h-3 bg-slate-200 rounded animate-pulse w-5/6" />
        </div>
      ) : (
        children
      )}
    </section>
  );
};

export default Card;
