import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from 'react-query';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  CartesianGrid,
} from 'recharts';
import {
  useDashboardMetrics,
  useAlerts,
  useReports,
  useSources,
  useRunScanNow,
} from '../hooks/useDetection';
import { useWebSocket } from '../hooks/useWebSocket';
import { useAuth } from '../context/AuthContext';
import { detectionService, AlertInfo } from '../services/detection.service';
import { formatDateTime } from '../utils/formatDate';
import {
  Card,
  KPITile,
  PageHeader,
  LiveIndicator,
  FilterBar,
  EmptyState,
  SeverityRail,
  SeverityBadge,
  SEVERITY_STYLES,
  normalizeSeverity,
  SeverityLevel,
} from '../components/ui';
import { SHORTCUT_EVENTS } from '../hooks/useKeyboardShortcuts';

const SOURCE_COLORS = [
  '#3B82F6',
  '#10B981',
  '#F59E0B',
  '#8B5CF6',
  '#EF4444',
  '#0EA5E9',
  '#EC4899',
  '#64748B',
];

const TIME_RANGE_OPTIONS = [
  { value: '1h', label: 'Last 1h', ms: 60 * 60 * 1000 },
  { value: '24h', label: 'Last 24h', ms: 24 * 60 * 60 * 1000 },
  { value: '7d', label: 'Last 7d', ms: 7 * 24 * 60 * 60 * 1000 },
  { value: '30d', label: 'Last 30d', ms: 30 * 24 * 60 * 60 * 1000 },
];

const SEVERITY_ORDER: SeverityLevel[] = ['low', 'medium', 'high', 'critical'];

function bucketByHour(alerts: AlertInfo[], windowMs: number): Array<{
  hour: string;
  low: number;
  medium: number;
  high: number;
  critical: number;
}> {
  const now = Date.now();
  const start = now - windowMs;
  // Always 24 hourly buckets covering the last 24h (independent of range).
  const buckets: Array<{ hour: string; low: number; medium: number; high: number; critical: number }> = [];
  const windowMsClamped = Math.max(windowMs, 60 * 60 * 1000); // at least 1h
  const slotMs = windowMsClamped / 24;
  for (let i = 0; i < 24; i++) {
    const d = new Date(start + i * slotMs);
    buckets.push({
      hour: `${d.getHours().toString().padStart(2, '0')}:00`,
      low: 0,
      medium: 0,
      high: 0,
      critical: 0,
    });
  }
  for (const a of alerts) {
    const t = Date.parse(a.created_at);
    if (!Number.isFinite(t) || t < start || t > now) continue;
    const idx = Math.min(23, Math.floor((t - start) / slotMs));
    const lvl = normalizeSeverity(a.threat_level);
    buckets[idx][lvl] += 1;
  }
  return buckets;
}

function hourlyAnalysesSpark(items: Array<{ created_at: string }>): number[] {
  // 24 hourly buckets across last 24h — used for the Analyses tile sparkline.
  const now = Date.now();
  const start = now - 24 * 60 * 60 * 1000;
  const buckets = new Array<number>(24).fill(0);
  for (const it of items) {
    const t = Date.parse(it.created_at);
    if (!Number.isFinite(t) || t < start || t > now) continue;
    const idx = Math.min(23, Math.floor((t - start) / (60 * 60 * 1000)));
    buckets[idx] += 1;
  }
  return buckets;
}

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const [timeRange, setTimeRange] = useState<string>('24h');
  const [filterSeverity, setFilterSeverity] = useState<string>('');
  const [filterSource, setFilterSource] = useState<string>('');
  const [filterSearch, setFilterSearch] = useState<string>('');
  const searchInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handler = () => searchInputRef.current?.focus();
    window.addEventListener(SHORTCUT_EVENTS.focusSearch, handler);
    return () => window.removeEventListener(SHORTCUT_EVENTS.focusSearch, handler);
  }, []);

  const {
    data: metrics,
    isLoading: metricsLoading,
    dataUpdatedAt: metricsUpdatedAt,
  } = useDashboardMetrics();
  const {
    data: alerts,
    isLoading: alertsLoading,
    dataUpdatedAt: alertsUpdatedAt,
  } = useAlerts();
  const { data: reports } = useReports();
  const { data: sources } = useSources();
  const runScanMutation = useRunScanNow();
  useWebSocket();

  const allAlerts: AlertInfo[] = useMemo(() => alerts ?? [], [alerts]);

  const windowMs = useMemo(
    () => TIME_RANGE_OPTIONS.find((r) => r.value === timeRange)?.ms ?? 24 * 60 * 60 * 1000,
    [timeRange],
  );

  const alertsInWindow = useMemo(() => {
    const cutoff = Date.now() - windowMs;
    return allAlerts.filter((a) => {
      const t = Date.parse(a.created_at);
      return Number.isFinite(t) && t >= cutoff;
    });
  }, [allAlerts, windowMs]);

  // ----- KPI derivations -----

  const totalAnalyses = metrics?.total_analyses ?? 0;
  const analysesToday = metrics?.analyses_today ?? 0;
  const criticalAlerts = metrics?.critical_alerts ?? 0;
  const avgThreatScore = metrics?.avg_threat_score ?? 0;
  const trend24h = metrics?.threat_trend_24h ?? null;
  const activeSources = metrics?.active_sources ?? 0;

  const unreadCount = useMemo(
    () => allAlerts.filter((a) => !a.is_read && !a.is_resolved).length,
    [allAlerts],
  );
  const openCount = useMemo(
    () => allAlerts.filter((a) => !a.is_resolved).length,
    [allAlerts],
  );

  // Sparkline for "Total Analyses" — derive from alerts in last 24h.
  // (Closest proxy without a new API; falls back to flat if no data.)
  const analysesSpark = useMemo(
    () => hourlyAnalysesSpark(allAlerts),
    [allAlerts],
  );

  const sourceBreakdownSummary = useMemo(() => {
    const entries = Object.entries(metrics?.source_breakdown ?? {});
    if (entries.length === 0) return '—';
    return entries
      .sort((a, b) => b[1] - a[1])
      .map(([name, count]) => `${count} ${name}`)
      .join(' · ');
  }, [metrics?.source_breakdown]);

  const allSourcesActive = useMemo(() => {
    const list = sources ?? [];
    return list.length > 0 && list.every((s) => s.is_active);
  }, [sources]);

  // ----- Chart data -----

  const stackedHourly = useMemo(
    () => bucketByHour(alertsInWindow, windowMs),
    [alertsInWindow, windowMs],
  );

  const severityMixData = useMemo(() => {
    const counts: Record<SeverityLevel, number> = {
      critical: 0,
      high: 0,
      medium: 0,
      low: 0,
    };
    for (const a of allAlerts) {
      if (a.is_resolved) continue;
      counts[normalizeSeverity(a.threat_level)] += 1;
    }
    return (Object.keys(counts) as SeverityLevel[]).map((lvl) => ({
      name: lvl,
      value: counts[lvl],
      color: SEVERITY_STYLES[lvl].accent,
    }));
  }, [allAlerts]);

  const totalOpenAlerts = severityMixData.reduce((s, d) => s + d.value, 0);

  const sourceBars = useMemo(() => {
    const entries = Object.entries(metrics?.source_breakdown ?? {}).sort(
      (a, b) => b[1] - a[1],
    );
    const max = entries.length > 0 ? entries[0][1] : 0;
    return entries.map(([name, count], idx) => ({
      name,
      count,
      max,
      color: SOURCE_COLORS[idx % SOURCE_COLORS.length],
    }));
  }, [metrics?.source_breakdown]);

  // ----- Keywords strip -----
  const topKeywords = useMemo(() => {
    const counts = new Map<string, number>();
    for (const r of reports ?? []) {
      for (const kw of r.keywords ?? []) {
        const key = kw.trim().toLowerCase();
        if (!key) continue;
        counts.set(key, (counts.get(key) ?? 0) + 1);
      }
    }
    return Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10);
  }, [reports]);

  // ----- Alert stream filtering -----

  const sourceOptions = useMemo(
    () =>
      (sources ?? []).map((s) => ({ value: s.name, label: s.name })),
    [sources],
  );

  const filteredStream = useMemo(() => {
    const s = filterSearch.trim().toLowerCase();
    return allAlerts
      .filter((a) => {
        if (filterSeverity && normalizeSeverity(a.threat_level) !== filterSeverity) {
          return false;
        }
        if (filterSource && a.source_name !== filterSource) return false;
        if (s) {
          const hay = `${a.title} ${a.description ?? ''} ${a.source ?? ''}`.toLowerCase();
          if (!hay.includes(s)) return false;
        }
        return true;
      })
      .slice(0, 8);
  }, [allAlerts, filterSeverity, filterSource, filterSearch]);

  // ----- Actions -----

  const handleAck = async (id: string) => {
    try {
      await detectionService.markAlertRead(id);
      queryClient.invalidateQueries('alerts');
    } catch {
      /* handled */
    }
  };
  const handleResolve = async (id: string) => {
    try {
      await detectionService.resolveAlert(id);
      queryClient.invalidateQueries('alerts');
    } catch {
      /* handled */
    }
  };

  // ----- Render -----

  return (
    <div className="space-y-6">
      <PageHeader
        title="Operations Overview"
        subtitle={
          <>
            <span>Real-time threat detection across all monitored sources</span>
            <LiveIndicator dataUpdatedAt={metricsUpdatedAt} />
          </>
        }
        actions={
          <>
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              className="h-9 px-3 text-sm border border-slate-200 rounded-md bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500"
              aria-label="Time range"
            >
              {TIME_RANGE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => runScanMutation.mutate()}
              disabled={runScanMutation.isLoading}
              className="h-9 px-3 text-sm font-medium bg-primary-600 hover:bg-primary-700 text-white rounded-md disabled:opacity-50"
            >
              ↻ {runScanMutation.isLoading ? 'Scanning…' : 'Run scan now'}
            </button>
          </>
        }
      />

      {/* Row 1 — KPI tiles */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPITile
          label="Total Analyses"
          value={totalAnalyses.toLocaleString()}
          accent="blue"
          loading={metricsLoading}
          delta={
            analysesToday > 0
              ? {
                  value: analysesToday,
                  label: `+${analysesToday} today`,
                  direction: 'up',
                  semantic: 'neutral',
                }
              : undefined
          }
          sparklineData={analysesSpark}
        />
        <KPITile
          label="Critical Alerts"
          value={criticalAlerts}
          accent="red"
          loading={metricsLoading}
          hint={
            <>
              <span className="font-mono">{unreadCount}</span> unacknowledged ·{' '}
              <span className="font-mono">{openCount}</span> open
            </>
          }
        />
        <KPITile
          label="Avg Threat Score"
          value={<span className="font-mono">{avgThreatScore.toFixed(3)}</span>}
          accent="purple"
          loading={metricsLoading}
          delta={
            typeof trend24h === 'number' && trend24h !== 0
              ? {
                  value: trend24h,
                  label: `${trend24h > 0 ? '+' : ''}${trend24h.toFixed(4)}`,
                  direction: trend24h > 0 ? 'up' : 'down',
                  semantic: trend24h > 0 ? 'negative' : 'positive',
                }
              : undefined
          }
          hint="vs prev 24h"
        />
        <KPITile
          label="Active Sources"
          value={activeSources}
          accent="green"
          loading={metricsLoading}
          hint={sourceBreakdownSummary}
          delta={
            allSourcesActive
              ? {
                  value: 1,
                  label: 'All healthy',
                  direction: 'neutral',
                  semantic: 'positive',
                }
              : undefined
          }
        />
      </div>

      {/* Row 2 — Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card
          title="Threat activity (24h)"
          subtitle="Hourly volume stacked by severity"
          className="lg:col-span-2"
          loading={alertsLoading}
        >
          {stackedHourly.length > 0 ? (
            <div className="h-[260px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stackedHourly} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                  <XAxis
                    dataKey="hour"
                    tick={{ fill: '#64748B', fontSize: 11 }}
                    interval={5}
                  />
                  <YAxis tick={{ fill: '#64748B', fontSize: 11 }} allowDecimals={false} />
                  <Tooltip />
                  {SEVERITY_ORDER.map((lvl) => (
                    <Bar
                      key={lvl}
                      dataKey={lvl}
                      stackId="severity"
                      fill={SEVERITY_STYLES[lvl].accent}
                      name={lvl.charAt(0).toUpperCase() + lvl.slice(1)}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="No activity in this window" description="Alerts will appear here as they arrive." />
          )}
        </Card>

        <Card title="Severity mix" subtitle="Open alerts" loading={alertsLoading}>
          {totalOpenAlerts > 0 ? (
            <>
              <div className="relative h-[180px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={severityMixData.filter((d) => d.value > 0)}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={2}
                      dataKey="value"
                      nameKey="name"
                      onClick={(entry: any) =>
                        navigate(`/monitoring?severity=${entry?.name ?? ''}`)
                      }
                      style={{ cursor: 'pointer' }}
                    >
                      {severityMixData.map((entry) => (
                        <Cell key={entry.name} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <p className="text-xs text-slate-500">Open</p>
                  <p className="text-2xl font-bold text-slate-900 font-mono">{totalOpenAlerts}</p>
                </div>
              </div>
              <ul className="mt-3 space-y-1 text-xs">
                {severityMixData.map((d) => {
                  const pct = totalOpenAlerts > 0 ? Math.round((d.value / totalOpenAlerts) * 100) : 0;
                  return (
                    <li
                      key={d.name}
                      className="flex items-center justify-between hover:bg-slate-50 rounded px-1 py-0.5 cursor-pointer"
                      onClick={() => navigate(`/monitoring?severity=${d.name}`)}
                    >
                      <span className="flex items-center gap-2">
                        <span
                          className="inline-block h-2 w-2 rounded-full"
                          style={{ backgroundColor: d.color }}
                        />
                        <span className="capitalize text-slate-700">{d.name}</span>
                      </span>
                      <span className="font-mono text-slate-600">
                        {d.value} · {pct}%
                      </span>
                    </li>
                  );
                })}
              </ul>
            </>
          ) : (
            <EmptyState title="No open alerts" description="All clear right now." />
          )}
        </Card>
      </div>

      {/* Row 3 — Source breakdown + Model health */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card
          title="Source breakdown"
          subtitle="Items collected (24h)"
          className="lg:col-span-2"
          loading={metricsLoading}
        >
          {sourceBars.length > 0 ? (
            <ul className="space-y-3">
              {sourceBars.map((s) => {
                const pct = s.max > 0 ? Math.round((s.count / s.max) * 100) : 0;
                return (
                  <li
                    key={s.name}
                    className="cursor-pointer group"
                    onClick={() => navigate(`/monitor?source=${encodeURIComponent(s.name)}`)}
                  >
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-slate-700 group-hover:text-primary-600 capitalize">
                        {s.name}
                      </span>
                      <span className="font-mono text-slate-600">{s.count}</span>
                    </div>
                    <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{ width: `${pct}%`, backgroundColor: s.color }}
                      />
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : (
            <EmptyState title="No source activity" description="Add sources from Monitoring to see breakdowns." />
          )}
        </Card>

        <Card title="Detection model" loading={metricsLoading}>
          <div className="space-y-3">
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-wide">Active</p>
              <p className="text-base font-semibold text-slate-900">
                {metrics?.active_model ?? '—'}
              </p>
            </div>
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-slate-500 uppercase tracking-wide">F1 score</span>
                <span className="font-mono text-slate-700">
                  {metrics?.model_f1 != null ? metrics.model_f1.toFixed(3) : '—'}
                </span>
              </div>
              <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary-500 rounded-full"
                  style={{
                    width: `${
                      metrics?.model_f1 != null ? Math.round(metrics.model_f1 * 100) : 0
                    }%`,
                  }}
                />
              </div>
            </div>
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-wide">Last trained</p>
              {/* TODO: backend does not yet expose `model_trained_at`; surface a static dash. */}
              <p className="text-sm text-slate-700">—</p>
            </div>
            {user?.role === 'admin' && (
              <button
                type="button"
                onClick={() => navigate('/admin/users')}
                className="w-full text-sm py-1.5 border border-primary-600 text-primary-600 rounded hover:bg-primary-50"
              >
                View training
              </button>
            )}
          </div>
        </Card>
      </div>

      {/* Row 4 — Live alert stream */}
      <Card
        title={
          <span className="flex items-center gap-3">
            Live alert stream
            <LiveIndicator dataUpdatedAt={alertsUpdatedAt} />
          </span>
        }
        action={
          <button
            type="button"
            onClick={() => navigate('/monitoring')}
            className="text-xs text-primary-600 hover:underline"
          >
            View all →
          </button>
        }
      >
        <FilterBar
          severity={filterSeverity}
          source={filterSource}
          search={filterSearch}
          onSeverityChange={setFilterSeverity}
          onSourceChange={setFilterSource}
          onSearchChange={setFilterSearch}
          sourceOptions={sourceOptions}
          searchInputRef={searchInputRef}
          className="mb-3"
        />
        {alertsLoading ? (
          <div className="space-y-2">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-12 bg-slate-100 rounded animate-pulse" />
            ))}
          </div>
        ) : filteredStream.length > 0 ? (
          <ul className="space-y-1">
            {filteredStream.map((a) => {
              const lvl = normalizeSeverity(a.threat_level);
              return (
                <li
                  key={a.id}
                  className={`flex items-stretch border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors overflow-hidden ${
                    a.is_resolved ? 'opacity-60' : ''
                  }`}
                >
                  <SeverityRail level={lvl} />
                  <div className="flex-1 min-w-0 flex items-center gap-3 px-3 py-2">
                    <SeverityBadge level={lvl} size="sm" />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm text-slate-900 truncate">{a.title}</p>
                      <p className="text-xs text-slate-500 truncate">
                        {a.source_name ?? a.source ?? 'Unknown'} · {formatDateTime(a.created_at)} ·
                        <span className="font-mono"> score {a.threat_score.toFixed(3)}</span>
                      </p>
                    </div>
                    <div className="flex gap-1 flex-shrink-0">
                      {!a.is_read && (
                        <button
                          type="button"
                          onClick={() => handleAck(a.id)}
                          className="text-xs px-2 py-1 rounded bg-primary-600 text-white hover:bg-primary-700"
                        >
                          Ack
                        </button>
                      )}
                      {!a.is_resolved && (
                        <button
                          type="button"
                          onClick={() => handleResolve(a.id)}
                          className="text-xs px-2 py-1 rounded border border-slate-300 text-slate-700 hover:bg-slate-100"
                        >
                          Resolve
                        </button>
                      )}
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        ) : (
          <EmptyState
            title="No active alerts"
            description={
              alertsUpdatedAt
                ? `Last scan completed ${Math.max(
                    0,
                    Math.round((Date.now() - alertsUpdatedAt) / 60000),
                  )} minute(s) ago`
                : 'Waiting for first scan'
            }
          />
        )}
      </Card>

      {/* Row 5 — Top keywords */}
      {topKeywords.length > 0 && (
        <Card title="Top keywords" subtitle="Most frequent across recent reports">
          <div className="flex gap-2 overflow-x-auto pb-1">
            {topKeywords.map(([kw, count]) => (
              <button
                key={kw}
                type="button"
                onClick={() => setFilterSearch(kw)}
                className="flex-shrink-0 inline-flex items-center gap-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1 rounded-full text-xs transition-colors"
              >
                <span>{kw}</span>
                <span className="font-mono text-slate-500">{count}</span>
              </button>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};

export default Dashboard;
