import React, { useState } from 'react';
import { useFlaggedPosts, useMarkReviewed, useTriggerScan, useSearchReddit } from '../hooks/useReddit';
import ThreatBadge from '../components/ThreatBadge';
import { format, parseISO } from 'date-fns';

const ExtremismContent: React.FC = () => {
  const [threatFilter, setThreatFilter] = useState<string>('');
  const [subredditFilter, setSubredditFilter] = useState<string>('');
  const [daysFilter, setDaysFilter] = useState(30);
  const [selectedPost, setSelectedPost] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const { data: posts, isLoading } = useFlaggedPosts({
    threat_level: threatFilter || undefined,
    subreddit: subredditFilter || undefined,
    days: daysFilter,
    limit: 100,
  });

  const markReviewed = useMarkReviewed();
  const scanMutation = useTriggerScan();
  const searchMutation = useSearchReddit();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      searchMutation.mutate({ query: searchQuery.trim(), limit: 25 });
    }
  };

  const uniqueSubreddits = Array.from(new Set((posts || []).map((p) => p.subreddit))).sort();
  const detail = selectedPost !== null ? (posts || []).find((p) => p.id === selectedPost) : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Extremism Content</h2>
          <p className="text-sm text-gray-500 mt-1">
            Flagged Reddit posts analyzed for extremist content
          </p>
        </div>
        <button
          onClick={() => scanMutation.mutate({})}
          disabled={scanMutation.isLoading}
          className="bg-primary-600 text-white py-2 px-4 rounded-md hover:bg-primary-700 text-sm font-medium disabled:opacity-50"
        >
          {scanMutation.isLoading ? 'Scanning...' : 'Run Scan Now'}
        </button>
      </div>

      {/* Search */}
      <div className="bg-white rounded-lg shadow p-4">
        <form onSubmit={handleSearch} className="flex gap-3">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search Reddit for specific terms..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
          />
          <button
            type="submit"
            disabled={searchMutation.isLoading || !searchQuery.trim()}
            className="bg-gray-800 text-white py-2 px-4 rounded-md hover:bg-gray-900 text-sm font-medium disabled:opacity-50"
          >
            {searchMutation.isLoading ? 'Searching...' : 'Search Reddit'}
          </button>
        </form>
      </div>

      {/* Search Results */}
      {searchMutation.data && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">
              Search Results for &quot;{searchMutation.data.query}&quot;
              <span className="text-sm font-normal text-gray-500 ml-2">
                ({searchMutation.data.total_results} results)
              </span>
            </h3>
            <button
              onClick={() => searchMutation.reset()}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Clear
            </button>
          </div>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {searchMutation.data.posts.map((post) => (
              <div key={post.reddit_id} className="border rounded-lg p-3 hover:bg-gray-50">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <a
                      href={post.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm font-medium text-primary-600 hover:underline line-clamp-1"
                    >
                      {post.title}
                    </a>
                    <p className="text-xs text-gray-500 mt-0.5">
                      r/{post.subreddit} · u/{post.author} · {post.score} pts
                    </p>
                    {post.text && (
                      <p className="text-xs text-gray-600 mt-1 line-clamp-2">{post.text}</p>
                    )}
                  </div>
                  <ThreatBadge level={post.threat_level} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-wrap gap-3 items-center">
          <span className="text-sm font-medium text-gray-700">Filters:</span>
          <select
            value={threatFilter}
            onChange={(e) => setThreatFilter(e.target.value)}
            className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All Threat Levels</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <select
            value={subredditFilter}
            onChange={(e) => setSubredditFilter(e.target.value)}
            className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All Subreddits</option>
            {uniqueSubreddits.map((sub) => (
              <option key={sub} value={sub}>r/{sub}</option>
            ))}
          </select>
          <select
            value={daysFilter}
            onChange={(e) => setDaysFilter(Number(e.target.value))}
            className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
          <span className="text-sm text-gray-500 ml-auto">
            {posts?.length ?? 0} flagged posts
          </span>
        </div>
      </div>

      {/* Post Detail Modal */}
      {detail && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4" onClick={() => setSelectedPost(null)}>
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-lg font-semibold pr-4">{detail.title}</h3>
              <button onClick={() => setSelectedPost(null)} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
            </div>
            <div className="flex flex-wrap gap-2 mb-4">
              <ThreatBadge level={detail.threat_level} />
              <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">r/{detail.subreddit}</span>
              <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">u/{detail.author}</span>
              <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{detail.score} pts · {detail.num_comments} comments</span>
            </div>
            <div className="mb-4">
              <span className="text-sm font-medium">Threat Score: </span>
              <span className="text-sm font-bold text-red-600">{(detail.threat_score * 100).toFixed(1)}%</span>
            </div>
            {detail.text && (
              <div className="mb-4 bg-gray-50 rounded p-3">
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{detail.text}</p>
              </div>
            )}
            {detail.analysis_details && (
              <div className="mb-4">
                <h4 className="text-sm font-medium mb-2">Analysis Details</h4>
                <pre className="text-xs bg-gray-50 rounded p-3 overflow-x-auto">
                  {JSON.stringify(detail.analysis_details, null, 2)}
                </pre>
              </div>
            )}
            <div className="flex items-center justify-between pt-4 border-t">
              <div className="text-xs text-gray-500">
                {detail.posted_at && (
                  <span>Posted: {(() => { try { return format(parseISO(detail.posted_at), 'MMM dd, yyyy HH:mm'); } catch { return detail.posted_at; } })()}</span>
                )}
                {detail.scanned_at && (
                  <span className="ml-3">Scanned: {(() => { try { return format(parseISO(detail.scanned_at), 'MMM dd, yyyy HH:mm'); } catch { return detail.scanned_at; } })()}</span>
                )}
              </div>
              <div className="flex gap-2">
                <a
                  href={detail.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-primary-600 hover:underline"
                >
                  View on Reddit
                </a>
                {!detail.is_reviewed && (
                  <button
                    onClick={() => { markReviewed.mutate(detail.id); setSelectedPost(null); }}
                    className="text-sm bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700"
                  >
                    Mark Reviewed
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Posts Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {isLoading ? (
          <p className="text-gray-500 text-center py-12">Loading flagged posts...</p>
        ) : !posts || posts.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500">No flagged posts found.</p>
            <p className="text-sm text-gray-400 mt-1">Run a scan to start detecting extremist content.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Post</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Subreddit</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Threat</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Score</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {posts.map((post) => (
                  <tr key={post.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => setSelectedPost(post.id)}>
                    <td className="px-4 py-3">
                      <p className="text-sm font-medium text-gray-900 line-clamp-1 max-w-xs">{post.title}</p>
                      <p className="text-xs text-gray-500">u/{post.author} · {post.score} pts · {post.num_comments} comments</p>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">r/{post.subreddit}</td>
                    <td className="px-4 py-3"><ThreatBadge level={post.threat_level} /></td>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{(post.threat_score * 100).toFixed(1)}%</td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {post.scanned_at
                        ? (() => { try { return format(parseISO(post.scanned_at), 'MMM dd, HH:mm'); } catch { return 'N/A'; } })()
                        : 'N/A'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        post.is_reviewed ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                      }`}>
                        {post.is_reviewed ? 'Reviewed' : 'Pending'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                        <a
                          href={post.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-primary-600 hover:underline"
                        >
                          Reddit
                        </a>
                        {!post.is_reviewed && (
                          <button
                            onClick={() => markReviewed.mutate(post.id)}
                            className="text-xs text-green-600 hover:underline"
                          >
                            Review
                          </button>
                        )}
                      </div>
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

export default ExtremismContent;
