import React from 'react';
import { useDashboardMetrics, useAlerts } from '../hooks/useDetection';
import { useWebSocket } from '../hooks/useWebSocket';
import { detectionService, AlertInfo } from '../services/detection.service';
import { useQueryClient } from 'react-query';
import { formatDateTime } from '../utils/formatDate';
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
  Legend,
} from 'recharts';

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308',
  low: '#3b82f6',
};

const CATEGORY_COLORS: Record<string, string> = {
  violence: '#dc2626',
  extremism: '#b45309',
  planning: '#1d4ed8',
  financing: '#6d28d9',
};

const Dashboard: React.FC = () => {
  const { data: metrics, isLoading: metricsLoading } = useDashboardMetrics();
  const { data: alerts, isLoading: alertsLoading } = useAlerts();
  const { connected } = useWebSocket();
  const queryClient = useQueryClient();

  const recentAlerts = (alerts ?? []).slice(0, 8);

  // Category breakdown data for horizontal bar chart
  const categoryData = Object.entries(metrics?.category_breakdown ?? {}).map(
    ([name, value]) => ({ name, value }),
  );

  // Alert distribution data for donut chart
  const alertDistribution = [
    { name: 'Critical', value: metrics?.critical_alerts ?? 0, color: SEVERITY_COLORS.critical },
    { name: 'High', value: metrics?.high_alerts ?? 0, color: SEVERITY_COLORS.high },
    { name: 'Medium', value: metrics?.medium_alerts ?? 0, color: SEVERITY_COLORS.medium },
    { name: 'Low', value: metrics?.low_alerts ?? 0, color: SEVERITY_COLORS.low },
  ].filter((d) => d.value > 0);

  // Source breakdown
  // Source breakdown — ensure preferred order: reddit, upload, text, then rest
  const SOURCE_ORDER: Record<string, number> = { reddit: 0, upload: 1, text: 2 };
  const sourceEntries = Object.entries(metrics?.source_breakdown ?? {}).sort(
    ([a], [b]) => (SOURCE_ORDER[a] ?? 99) - (SOURCE_ORDER[b] ?? 99),
  );
  const maxSourceCount = Math.max(1, ...sourceEntries.map(([, v]) => v));

  const handleAcknowledge = async (id: string) => {
    try {
      await detectionService.markAlertRead(id);
      queryClient.invalidateQueries('alerts');
    } catch {
      // handled by interceptor
    }
  };

  const handleResolve = async (id: string) => {
    try {
      await detectionService.resolveAlert(id);
      queryClient.invalidateQueries('alerts');
    } catch {
      // handled by interceptor
    }
  };

  const trendPositive = (metrics?.threat_trend_24h ?? 0) > 0;
  const trendNeutral = (metrics?.threat_trend_24h ?? 0) === 0;

  return (
    <div className="space-y-6">
      {/* WebSocket status */}
      <div className="flex justify-end items-center gap-2">
        <span
          className={`inline-block h-2.5 w-2.5 rounded-full ${
            connected ? 'bg-green-500 animate-pulse' : 'bg-slate-500'
          }`}
        />
        <span className={`text-xs font-medium ${connected ? 'text-green-400' : 'text-slate-500'}`}>
          {connected ? 'LIVE' : 'Reconnecting\u2026'}
        </span>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Analyses */}
        <div className="rounded-lg border p-4 bg-blue-500/10 text-blue-400 border-blue-500/20">
          <p className="text-sm font-medium opacity-80">Total Analyses</p>
          <p className="text-2xl font-bold mt-1">
            {metricsLoading ? '...' : metrics?.total_analyses ?? 0}
          </p>
          {!metricsLoading && (metrics?.analyses_today ?? 0) > 0 && (
            <p className="text-xs mt-1 text-blue-400">+{metrics?.analyses_today} today</p>
          )}
        </div>

        {/* Critical Alerts */}
        <div className="rounded-lg border p-4 bg-red-500/10 text-red-400 border-red-500/20">
          <p className="text-sm font-medium opacity-80">Critical Alerts</p>
          <p className="text-2xl font-bold mt-1">
            {metricsLoading ? '...' : metrics?.critical_alerts ?? 0}
          </p>
          {!metricsLoading && trendPositive && (
            <p className="text-xs mt-1 text-red-400">Threat rising</p>
          )}
        </div>

        {/* Avg Threat Score */}
        <div className="rounded-lg border p-4 bg-purple-500/10 text-purple-400 border-purple-500/20">
          <p className="text-sm font-medium opacity-80">Avg Threat Score</p>
          <p className="text-2xl font-bold mt-1">
            {metricsLoading ? '...' : (metrics?.avg_threat_score ?? 0).toFixed(3)}
          </p>
          {!metricsLoading && !trendNeutral && (
            <p
              className={`text-xs mt-1 ${trendPositive ? 'text-red-400' : 'text-green-400'}`}
            >
              {trendPositive ? '\u25B2' : '\u25BC'}{' '}
              {Math.abs(metrics?.threat_trend_24h ?? 0).toFixed(4)} (24h)
            </p>
          )}
        </div>

        {/* Active Model */}
        <div className="rounded-lg border p-4 bg-green-500/10 text-green-400 border-green-500/20">
          <p className="text-sm font-medium opacity-80">Active Model</p>
          <p className="text-lg font-bold mt-1 truncate" title={metrics?.active_model}>
            {metricsLoading ? '...' : metrics?.active_model ?? 'N/A'}
          </p>
          {!metricsLoading && (metrics?.model_f1 ?? 0) > 0 && (
            <span className="inline-block mt-1 text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded">
              F1: {((metrics?.model_f1 ?? 0) * 100).toFixed(1)}%
            </span>
          )}
        </div>
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category breakdown — horizontal bar chart */}
        <div className="bg-panel rounded-lg border border-edge p-6">
          <h3 className="text-lg font-semibold mb-4 text-slate-100">Category Breakdown (24h)</h3>
          {categoryData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={categoryData} layout="vertical" margin={{ left: 10 }}>
                <XAxis type="number" />
                <YAxis type="category" dataKey="name" width={80} />
                <Tooltip />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {categoryData.map((entry) => (
                    <Cell
                      key={entry.name}
                      fill={CATEGORY_COLORS[entry.name] ?? '#6b7280'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-slate-500 text-center py-12">No category data yet</p>
          )}
        </div>

        {/* Alert distribution — donut chart */}
        <div className="bg-panel rounded-lg border border-edge p-6">
          <h3 className="text-lg font-semibold mb-4 text-slate-100">Alert Distribution</h3>
          {alertDistribution.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={alertDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={90}
                  paddingAngle={3}
                  dataKey="value"
                  nameKey="name"
                >
                  {alertDistribution.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
                <Legend />
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-slate-500 text-center py-12">No alerts to display</p>
          )}
        </div>
      </div>

      {/* Alert feed */}
      <div className="bg-panel rounded-lg border border-edge p-6">
        <h3 className="text-lg font-semibold mb-4 text-slate-100">Recent Alerts</h3>
        {alertsLoading ? (
          <p className="text-slate-500">Loading alerts...</p>
        ) : recentAlerts.length > 0 ? (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {recentAlerts.map((alert: AlertInfo) => {
              const dotColor = SEVERITY_COLORS[alert.threat_level] ?? '#6b7280';
              return (
                <div
                  key={alert.id}
                  className={`flex items-start gap-3 p-3 border border-edge rounded-lg ${
                    alert.is_resolved ? 'opacity-50' : ''
                  }`}
                >
                  {/* Severity dot */}
                  <span
                    className="mt-1.5 inline-block h-3 w-3 rounded-full flex-shrink-0"
                    style={{ backgroundColor: dotColor }}
                  />

                  <div className="flex-1 min-w-0">
                    <p
                      className={`font-medium text-sm ${
                        alert.is_resolved ? 'line-through text-slate-500' : 'text-slate-200'
                      }`}
                    >
                      {alert.title}
                    </p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {alert.source && <span>{alert.source} &middot; </span>}
                      {formatDateTime(alert.created_at)} &middot; Score:{' '}
                      {alert.threat_score.toFixed(3)}
                    </p>
                  </div>

                  <div className="flex gap-1 flex-shrink-0">
                    {!alert.is_read && (
                      <button
                        onClick={() => handleAcknowledge(alert.id)}
                        className="text-xs px-2 py-1 rounded bg-blue-500/15 text-blue-400 hover:bg-blue-500/25"
                      >
                        Acknowledge
                      </button>
                    )}
                    {!alert.is_resolved && (
                      <button
                        onClick={() => handleResolve(alert.id)}
                        className="text-xs px-2 py-1 rounded bg-green-500/15 text-green-400 hover:bg-green-500/25"
                      >
                        Resolve
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-slate-500">No alerts at this time.</p>
        )}
      </div>

      {/* Source breakdown mini cards */}
      {sourceEntries.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {sourceEntries.map(([name, count]) => (
            <div key={name} className="bg-panel rounded-lg border border-edge p-4">
              <p className="text-xs font-medium uppercase text-slate-500">{name}</p>
              <p className="text-xl font-bold mt-1 text-slate-100">{count}</p>
              <div className="w-full bg-slate-700 rounded-full h-1.5 mt-2">
                <div
                  className="bg-blue-500 h-1.5 rounded-full"
                  style={{ width: `${Math.round((count / maxSourceCount) * 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Dashboard;
