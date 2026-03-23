import React from 'react';
import { Doughnut } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';
import { DashboardMetrics } from '../services/detection.service';

ChartJS.register(ArcElement, Tooltip, Legend);

interface ThreatChartProps {
  metrics: DashboardMetrics | undefined;
}

const ThreatChart: React.FC<ThreatChartProps> = ({ metrics }) => {
  if (!metrics) {
    return <p className="text-gray-500 text-center py-8">Loading chart...</p>;
  }

  const data = {
    labels: ['Critical', 'High', 'Other Alerts'],
    datasets: [
      {
        data: [
          metrics.critical_alerts,
          metrics.high_alerts,
          Math.max(0, metrics.total_alerts - metrics.critical_alerts - metrics.high_alerts),
        ],
        backgroundColor: ['#ef4444', '#f97316', '#3b82f6'],
        borderColor: ['#dc2626', '#ea580c', '#2563eb'],
        borderWidth: 1,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: 'bottom' as const,
      },
    },
  };

  if (metrics.total_alerts === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500">No alerts to display</p>
        <p className="text-sm text-gray-400 mt-1">Alerts will appear here when detected</p>
      </div>
    );
  }

  return <Doughnut data={data} options={options} />;
};

export default ThreatChart;
