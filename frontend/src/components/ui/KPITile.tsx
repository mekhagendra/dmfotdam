import React, { useMemo } from 'react';
import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts';

const ACCENT: Record<string, string> = {
  blue: '#3B82F6',
  red: '#EF4444',
  amber: '#F59E0B',
  green: '#10B981',
  purple: '#8B5CF6',
};

export type TileAccent = 'blue' | 'red' | 'amber' | 'green' | 'purple';

export interface KPIDelta {
  /** Numeric delta value (display formatting is up to caller via label) */
  value: number;
  /** Display label, e.g. "+12 today" */
  label: string;
  /** Arrow direction */
  direction: 'up' | 'down' | 'neutral';
  /** Semantic meaning of the delta (drives badge color) */
  semantic: 'positive' | 'negative' | 'neutral';
}

export interface KPITileProps {
  /** Uppercase 11px label */
  label: string;
  /** Primary value (rendered at 24px bold) */
  value: React.ReactNode;
  /** Optional delta pill */
  delta?: KPIDelta;
  /** Optional numeric series for the mini sparkline */
  sparklineData?: number[];
  /** Accent color (drives sparkline + accent dot) */
  accent: TileAccent;
  /** Optional small hint line below the value */
  hint?: React.ReactNode;
  /** Loading state */
  loading?: boolean;
  /** Optional override classes */
  className?: string;
  /** Density (drives value font size) */
  density?: 'comfortable' | 'compact';
}

const DELTA_SEMANTIC: Record<KPIDelta['semantic'], string> = {
  positive: 'bg-emerald-100 text-emerald-700',
  negative: 'bg-red-100 text-red-700',
  neutral: 'bg-slate-100 text-slate-600',
};

const DIRECTION_GLYPH: Record<KPIDelta['direction'], string> = {
  up: '▲',
  down: '▼',
  neutral: '·',
};

/**
 * Compact KPI tile used in the dashboard top row. Composes <Card> styling.
 */
const KPITile: React.FC<KPITileProps> = ({
  label,
  value,
  delta,
  sparklineData,
  accent,
  hint,
  loading,
  className = '',
  density = 'comfortable',
}) => {
  const accentColor = ACCENT[accent];
  const valueSize = density === 'compact' ? 'text-[20px]' : 'text-[24px]';
  const padding = density === 'compact' ? 'p-3' : 'p-5';

  const sparkSeries = useMemo(
    () => (sparklineData ?? []).map((v, i) => ({ x: i, y: v })),
    [sparklineData],
  );

  return (
    <div
      className={`bg-white rounded-lg border border-slate-200 shadow-sm ${padding} flex flex-col gap-2 ${className}`}
    >
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          {label}
        </p>
        <span
          className="inline-block h-2 w-2 rounded-full"
          aria-hidden="true"
          style={{ backgroundColor: accentColor }}
        />
      </div>
      {loading ? (
        <div className="h-7 bg-slate-200 rounded animate-pulse w-1/2" />
      ) : (
        <p className={`font-bold text-slate-900 leading-none ${valueSize}`}>{value}</p>
      )}
      {!loading && delta && (
        <span
          className={`inline-flex items-center gap-1 self-start text-[11px] font-medium px-1.5 py-0.5 rounded ${DELTA_SEMANTIC[delta.semantic]}`}
        >
          <span aria-hidden="true">{DIRECTION_GLYPH[delta.direction]}</span>
          {delta.label}
        </span>
      )}
      {!loading && hint && <p className="text-xs text-slate-500">{hint}</p>}
      {!loading && sparkSeries.length > 1 && (
        <div className="h-[30px] -mx-1">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sparkSeries}>
              <YAxis hide domain={['auto', 'auto']} />
              <Line
                type="monotone"
                dataKey="y"
                stroke={accentColor}
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

export default KPITile;
