import React from 'react';

export type SkeletonVariant = 'card' | 'row' | 'chart' | 'tile';

export interface SkeletonProps {
  /** Visual variant */
  variant?: SkeletonVariant;
  /** Optional extra classes */
  className?: string;
}

/**
 * Generic loading skeleton — uses `animate-pulse bg-slate-200 rounded`.
 * Variants render different block shapes used across the dashboard.
 */
const Skeleton: React.FC<SkeletonProps> = ({ variant = 'row', className = '' }) => {
  if (variant === 'card') {
    return (
      <div className={`space-y-3 ${className}`} aria-busy="true">
        <div className="h-4 bg-slate-200 rounded animate-pulse w-1/3" />
        <div className="h-3 bg-slate-200 rounded animate-pulse w-2/3" />
        <div className="h-3 bg-slate-200 rounded animate-pulse w-5/6" />
        <div className="h-3 bg-slate-200 rounded animate-pulse w-1/2" />
      </div>
    );
  }
  if (variant === 'chart') {
    return (
      <div className={`h-[260px] bg-slate-100 rounded animate-pulse ${className}`} aria-busy="true" />
    );
  }
  if (variant === 'tile') {
    return (
      <div className={`space-y-2 ${className}`} aria-busy="true">
        <div className="h-3 bg-slate-200 rounded animate-pulse w-2/3" />
        <div className="h-7 bg-slate-200 rounded animate-pulse w-1/2" />
      </div>
    );
  }
  // row
  return (
    <div className={`h-4 bg-slate-200 rounded animate-pulse ${className}`} aria-busy="true" />
  );
};

export default Skeleton;
