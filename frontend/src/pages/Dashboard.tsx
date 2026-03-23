import React from 'react';
import { useDashboardMetrics, useAlerts } from '../hooks/useDetection';
import ThreatChart from '../components/ThreatChart';
import AlertList from '../components/AlertList';

const Dashboard: React.FC = () => {
  const { data: metrics, isLoading: metricsLoading } = useDashboardMetrics();
  const { data: alerts, isLoading: alertsLoading } = useAlerts();

  return (
    <div className="space-y-6">
      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Analyses"
          value={metrics?.total_analyses ?? 0}
          color="blue"
          loading={metricsLoading}
        />
        <MetricCard
          title="Active Alerts"
          value={metrics?.total_alerts ?? 0}
          color="yellow"
          loading={metricsLoading}
        />
        <MetricCard
          title="Critical Alerts"
          value={metrics?.critical_alerts ?? 0}
          color="red"
          loading={metricsLoading}
        />
        <MetricCard
          title="Avg Threat Score"
          value={metrics?.avg_threat_score?.toFixed(3) ?? '0.000'}
          color="purple"
          loading={metricsLoading}
        />
      </div>

      {/* Charts and Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Threat Overview</h3>
          <ThreatChart metrics={metrics} />
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Recent Alerts</h3>
          <AlertList alerts={alerts ?? []} loading={alertsLoading} />
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-2">Active Sources</h3>
          <p className="text-3xl font-bold text-primary-600">
            {metricsLoading ? '...' : metrics?.active_sources ?? 0}
          </p>
          <p className="text-sm text-gray-500 mt-1">Monitoring sources configured</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-2">High Priority</h3>
          <p className="text-3xl font-bold text-danger-600">
            {metricsLoading ? '...' : metrics?.high_alerts ?? 0}
          </p>
          <p className="text-sm text-gray-500 mt-1">Unresolved high-level alerts</p>
        </div>
      </div>
    </div>
  );
};

interface MetricCardProps {
  title: string;
  value: string | number;
  color: 'blue' | 'yellow' | 'red' | 'purple';
  loading: boolean;
}

const colorMap = {
  blue: 'bg-blue-50 text-blue-700 border-blue-200',
  yellow: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  red: 'bg-red-50 text-red-700 border-red-200',
  purple: 'bg-purple-50 text-purple-700 border-purple-200',
};

const MetricCard: React.FC<MetricCardProps> = ({ title, value, color, loading }) => (
  <div className={`rounded-lg border p-4 ${colorMap[color]}`}>
    <p className="text-sm font-medium opacity-80">{title}</p>
    <p className="text-2xl font-bold mt-1">{loading ? '...' : value}</p>
  </div>
);

export default Dashboard;
