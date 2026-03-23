import React from 'react';
import { useReports } from '../hooks/useDetection';
import ThreatBadge from '../components/ThreatBadge';

const Reports: React.FC = () => {
  const { data: reports, isLoading } = useReports();

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Analysis Reports</h2>

        {isLoading ? (
          <p className="text-gray-500">Loading reports...</p>
        ) : reports && reports.length > 0 ? (
          <div className="space-y-4">
            {reports.map((report) => (
              <div key={report.id} className="border rounded-lg p-4 hover:bg-gray-50">
                <>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-gray-500">#{report.id}</span>
                    <span className="text-xs bg-gray-100 px-2 py-0.5 rounded uppercase">
                      {report.analysis_type}
                    </span>
                    <ThreatBadge level={report.threat_level || 'low'} />
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${
                        report.status === 'completed'
                          ? 'bg-green-100 text-green-700'
                          : report.status === 'failed'
                          ? 'bg-red-100 text-red-700'
                          : 'bg-yellow-100 text-yellow-700'
                      }`}
                    >
                      {report.status}
                    </span>
                  </div>
                  <span className="text-xs text-gray-400">
                    {new Date(report.created_at).toLocaleString()}
                  </span>
                </div>

                {report.summary && (
                  <p className="text-sm text-gray-700 mb-2">{report.summary}</p>
                )}

                <div className="flex flex-wrap gap-4 text-sm">
                  {report.threat_score !== null && (
                    <span className="text-gray-500">
                      Score: <strong>{report.threat_score.toFixed(4)}</strong>
                    </span>
                  )}
                  {report.sentiment && (
                    <span className="text-gray-500">
                      Sentiment: <strong>{report.sentiment}</strong>
                    </span>
                  )}
                  {report.language && (
                    <span className="text-gray-500">
                      Language: <strong>{report.language}</strong>
                    </span>
                  )}
                </div>

                {report.keywords && report.keywords.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {report.keywords.slice(0, 10).map((kw, i) => (
                      <span
                        key={i}
                        className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded"
                      >
                        {kw}
                      </span>
                    ))}
                    {report.keywords.length > 10 && (
                      <span className="text-xs text-gray-400">
                        +{report.keywords.length - 10} more
                      </span>
                    )}
                  </div>
                )}

                {report.details && report.details.categories_detected && (
                  <div className="mt-2">
                    <span className="text-xs text-gray-500">Categories: </span>
                    {(report.details.categories_detected as string[]).map((cat: string, i: number) => (
                      <span
                        key={i}
                        className="text-xs bg-orange-50 text-orange-600 px-2 py-0.5 rounded mr-1"
                      >
                        {cat}
                      </span>
                    ))}
                  </div>
                )}
                </>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No analysis reports yet. Upload a document or analyze text to get started.</p>
        )}
      </div>
    </div>
  );
};

export default Reports;
