import React, { useState } from 'react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts';
import { useRedditTrends, useSubredditStats, useRedditStatus, useTriggerScan } from '../hooks/useReddit';
import { format, parseISO } from 'date-fns';

const COLORS = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#8b5cf6', '#ec4899'];

const Trends: React.FC = () => {
  const [days, setDays] = useState(30);
  const { data: trends, isLoading: trendsLoading } = useRedditTrends(days);
  const { data: subredditStats, isLoading: statsLoading } = useSubredditStats(days);
  const { data: status } = useRedditStatus();
  const scanMutation = useTriggerScan();

  const formattedTrends = (trends || []).map((t) => ({
    ...t,
    dateLabel: (() => { try { return format(parseISO(t.date), 'MMM dd'); } catch { return t.date; } })(),
    avg_threat_score: Number((t.avg_threat_score * 100).toFixed(1)),
    max_threat_score: Number((t.max_threat_score * 100).toFixed(1)),
  }));

  const totalPosts = subredditStats?.reduce((sum, s) => sum + s.total_posts, 0) ?? 0;
  const totalHighThreats = subredditStats?.reduce((sum, s) => sum + s.high_threat_count, 0) ?? 0;
  const avgScore = subredditStats && subredditStats.length > 0
    ? (subredditStats.reduce((sum, s) => sum + s.avg_threat_score, 0) / subredditStats.length)
    : 0;

  return (
    <div className="space-y-6">
      {/* Header with controls */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Reddit Threat Trends</h2>
          <p className="text-sm text-gray-500 mt-1">
            {status?.available
              ? `Monitoring ${status.default_subreddits.length} subreddits · ${status.total_stored_posts} posts stored`
              : 'Reddit API not configured'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
          <button
            onClick={() => scanMutation.mutate({})}
            disabled={scanMutation.isLoading}
            className="bg-primary-600 text-white py-2 px-4 rounded-md hover:bg-primary-700 text-sm font-medium disabled:opacity-50"
          >
            {scanMutation.isLoading ? 'Scanning...' : 'Run Scan Now'}
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <SummaryCard title="Total Posts Scanned" value={totalPosts} color="blue" />
        <SummaryCard title="High Threat Posts" value={totalHighThreats} color="red" />
        <SummaryCard title="Avg Threat Score" value={`${(avgScore * 100).toFixed(1)}%`} color="yellow" />
        <SummaryCard
          title="Last Scan"
          value={
            status?.last_scan_time
              ? (() => { try { return format(parseISO(status.last_scan_time), 'MMM dd, HH:mm'); } catch { return 'N/A'; } })()
              : 'Never'
          }
          color="purple"
        />
      </div>

      {/* Threat Score Timeline */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Threat Score Timeline</h3>
        {trendsLoading ? (
          <p className="text-gray-500 text-center py-12">Loading trends...</p>
        ) : formattedTrends.length === 0 ? (
          <p className="text-gray-500 text-center py-12">No trend data available. Run a scan to start collecting data.</p>
        ) : (
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={formattedTrends}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="dateLabel" fontSize={12} />
              <YAxis fontSize={12} unit="%" />
              <Tooltip formatter={(value: number) => [`${value}%`]} />
              <Legend />
              <Line type="monotone" dataKey="avg_threat_score" stroke="#eab308" name="Avg Threat %" strokeWidth={2} />
              <Line type="monotone" dataKey="max_threat_score" stroke="#ef4444" name="Max Threat %" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily Post Counts */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Daily Post Volume</h3>
          {trendsLoading ? (
            <p className="text-gray-500 text-center py-12">Loading...</p>
          ) : formattedTrends.length === 0 ? (
            <p className="text-gray-500 text-center py-12">No data</p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={formattedTrends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="dateLabel" fontSize={12} />
                <YAxis fontSize={12} />
                <Tooltip />
                <Legend />
                <Bar dataKey="total_posts" fill="#3b82f6" name="Total Posts" />
                <Bar dataKey="high_threat_count" fill="#ef4444" name="High Threat" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Subreddit Distribution */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Subreddit Distribution</h3>
          {statsLoading ? (
            <p className="text-gray-500 text-center py-12">Loading...</p>
          ) : !subredditStats || subredditStats.length === 0 ? (
            <p className="text-gray-500 text-center py-12">No data</p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={subredditStats}
                  dataKey="total_posts"
                  nameKey="subreddit"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={({ subreddit, percent }) => `r/${subreddit} (${(percent * 100).toFixed(0)}%)`}
                >
                  {subredditStats.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: number, name: string) => [value, `r/${name}`]} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Subreddit Stats Table */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Subreddit Statistics</h3>
        {statsLoading ? (
          <p className="text-gray-500">Loading...</p>
        ) : !subredditStats || subredditStats.length === 0 ? (
          <p className="text-gray-500">No subreddit data available.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Subreddit</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Posts</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Avg Score</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Max Score</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">High Threat</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {subredditStats.map((stat) => (
                  <tr key={stat.subreddit} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-primary-600">r/{stat.subreddit}</td>
                    <td className="px-4 py-3 text-sm text-gray-900">{stat.total_posts}</td>
                    <td className="px-4 py-3 text-sm text-gray-900">{(stat.avg_threat_score * 100).toFixed(1)}%</td>
                    <td className="px-4 py-3 text-sm text-gray-900">{(stat.max_threat_score * 100).toFixed(1)}%</td>
                    <td className="px-4 py-3 text-sm">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        stat.high_threat_count > 0 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                      }`}>
                        {stat.high_threat_count}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

const colorMap: Record<string, string> = {
  blue: 'bg-blue-50 text-blue-700 border-blue-200',
  yellow: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  red: 'bg-red-50 text-red-700 border-red-200',
  purple: 'bg-purple-50 text-purple-700 border-purple-200',
};

const SummaryCard: React.FC<{ title: string; value: string | number; color: string }> = ({ title, value, color }) => (
  <div className={`rounded-lg border p-4 ${colorMap[color] || colorMap.blue}`}>
    <p className="text-sm font-medium opacity-80">{title}</p>
    <p className="text-2xl font-bold mt-1">{value}</p>
  </div>
);

export default Trends;
