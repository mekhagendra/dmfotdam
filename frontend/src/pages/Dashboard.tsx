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
  high: '#dc2626',
  medium: '#f59e0b',
  low: '#16a34a',
  unknown: '#6b7280',
};

const Dashboard: React.FC = () => {
  const { data: metrics, isLoading: metricsLoading } = useDashboardMetrics();
  const { data: alerts, isLoading: alertsLoading } = useAlerts();
  useWebSocket();
  const queryClient = useQueryClient();

  const recentAlerts = (alerts ?? []).slice(0, 8);

  const hasNumber = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);

  // Category breakdown data for horizontal bar chart
  const categoryData = Object.entries(metrics?.category_breakdown ?? {}).map(
    ([name, value]) => ({ name, value }),
  );

  // Alert distribution data for donut chart
  const alertDistribution = [
    { name: 'Critical', value: metrics?.critical_alerts, color: SEVERITY_COLORS.critical },
    { name: 'High', value: metrics?.high_alerts, color: SEVERITY_COLORS.high },
    { name: 'Medium', value: metrics?.medium_alerts, color: SEVERITY_COLORS.medium },
    { name: 'Low', value: metrics?.low_alerts, color: SEVERITY_COLORS.low },
  ].filter((d) => hasNumber(d.value) && d.value > 0) as Array<{
    name: string;
    value: number;
    color: string;
  }>;

  // Source breakdown
  // Source breakdown — ensure preferred order: reddit, upload, text, then rest
  const SOURCE_ORDER: Record<string, number> = { reddit: 0, upload: 1, text: 2 };
  const sourceEntries = Object.entries(metrics?.source_breakdown ?? {}).sort(
    ([a], [b]) => (SOURCE_ORDER[a] ?? 99) - (SOURCE_ORDER[b] ?? 99),
  );
  const maxSourceCount = sourceEntries.length > 0 ? Math.max(...sourceEntries.map(([, v]) => v)) : 0;

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

  const trendValue = hasNumber(metrics?.threat_trend_24h) ? metrics?.threat_trend_24h : undefined;
  const trendPositive = typeof trendValue === 'number' && trendValue > 0;
  const trendNeutral = typeof trendValue === 'number' && trendValue === 0;
  const totalAnalyses = hasNumber(metrics?.total_analyses) ? metrics?.total_analyses : undefined;
  const analysesToday = hasNumber(metrics?.analyses_today) ? metrics?.analyses_today : undefined;
  const criticalAlerts = hasNumber(metrics?.critical_alerts) ? metrics?.critical_alerts : undefined;
  const avgThreatScore = hasNumber(metrics?.avg_threat_score) ? metrics?.avg_threat_score : undefined;


  return (
    <div className="space-y-6">
      {/* KPI Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Total Analyses */}
        <div className="rounded-lg border p-4 bg-blue-500/10 text-blue-400 border-blue-500/20">
          <p className="text-sm font-medium opacity-80">Total Analyses</p>
          <p className="text-2xl font-bold mt-1">
            {metricsLoading ? '...' : totalAnalyses ?? ''}
          </p>
          {!metricsLoading && typeof analysesToday === 'number' && analysesToday > 0 && (
            <p className="text-xs mt-1 text-blue-400">+{analysesToday} today</p>
          )}
        </div>

        {/* Critical Alerts */}
        <div className="rounded-lg border p-4 bg-red-500/10 text-red-400 border-red-500/20">
          <p className="text-sm font-medium opacity-80">Critical Alerts</p>
          <p className="text-2xl font-bold mt-1">
            {metricsLoading ? '...' : criticalAlerts ?? ''}
          </p>
          {!metricsLoading && trendPositive && (
            <p className="text-xs mt-1 text-red-400">Threat rising</p>
          )}
        </div>

        {/* Avg Threat Score */}
        <div className="rounded-lg border p-4 bg-purple-500/10 text-purple-400 border-purple-500/20">
          <p className="text-sm font-medium opacity-80">Avg Threat Score</p>
          <p className="text-2xl font-bold mt-1">
            {metricsLoading ? '...' : typeof avgThreatScore === 'number' ? avgThreatScore.toFixed(3) : ''}
          </p>
          {!metricsLoading && typeof trendValue === 'number' && !trendNeutral && (
            <p
              className={`text-xs mt-1 ${trendPositive ? 'text-red-400' : 'text-green-400'}`}
            >
              {trendPositive ? '\u25B2' : '\u25BC'}{' '}
              {Math.abs(trendValue).toFixed(4)} (24h)
            </p>
          )}
        </div>


      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category breakdown — horizontal bar chart */}
        <div className="bg-panel rounded-lg border border-edge p-6">
          <h3 className="text-lg font-semibold mb-4 text-slate-900">Threat Level Breakdown (24h)</h3>
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
          <h3 className="text-lg font-semibold mb-4 text-slate-900">Alert Distribution</h3>
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
        <h3 className="text-lg font-semibold mb-4 text-slate-900">Recent Alerts</h3>
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
                        alert.is_resolved ? 'line-through text-slate-500' : 'text-slate-800'
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
              <p className="text-xl font-bold mt-1 text-slate-900">{count}</p>
              <div className="w-full bg-slate-700 rounded-full h-1.5 mt-2">
                <div
                  className="bg-blue-500 h-1.5 rounded-full"
                  style={{ width: `${maxSourceCount > 0 ? Math.round((count / maxSourceCount) * 100) : 0}%` }}
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
