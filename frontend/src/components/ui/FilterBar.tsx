import React from 'react';

export interface FilterOption {
  value: string;
  label: string;
}

export interface FilterBarProps {
  /** Selected severity (empty string = "any") */
  severity: string;
  /** Selected source name (empty string = "any") */
  source: string;
  /** Search text */
  search: string;
  onSeverityChange: (value: string) => void;
  onSourceChange: (value: string) => void;
  onSearchChange: (value: string) => void;
  /** Source options to render */
  sourceOptions?: FilterOption[];
  /** Custom severity options (defaults to critical/high/medium/low) */
  severityOptions?: FilterOption[];
  /** Optional ref for focusing the search input externally (keyboard "/" shortcut) */
  searchInputRef?: React.RefObject<HTMLInputElement>;
  /** Optional override classes */
  className?: string;
}

const DEFAULT_SEVERITY_OPTIONS: FilterOption[] = [
  { value: '', label: 'All severities' },
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
];

/**
 * Controlled filter toolbar — severity dropdown, source dropdown, search input.
 * Used at the top of alert / item feeds.
 */
const FilterBar: React.FC<FilterBarProps> = ({
  severity,
  source,
  search,
  onSeverityChange,
  onSourceChange,
  onSearchChange,
  sourceOptions,
  severityOptions = DEFAULT_SEVERITY_OPTIONS,
  searchInputRef,
  className = '',
}) => {
  const baseInputClass =
    'h-8 text-xs px-2 border border-slate-200 rounded bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500';

  return (
    <div className={`flex flex-wrap items-center gap-2 ${className}`}>
      <select
        value={severity}
        onChange={(e) => onSeverityChange(e.target.value)}
        className={baseInputClass}
        aria-label="Filter by severity"
      >
        {severityOptions.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <select
        value={source}
        onChange={(e) => onSourceChange(e.target.value)}
        className={baseInputClass}
        aria-label="Filter by source"
      >
        <option value="">All sources</option>
        {(sourceOptions ?? []).map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <input
        ref={searchInputRef}
        type="search"
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder="Search…"
        className={`${baseInputClass} w-40 md:w-56`}
        aria-label="Search"
      />
    </div>
  );
};

export default FilterBar;
