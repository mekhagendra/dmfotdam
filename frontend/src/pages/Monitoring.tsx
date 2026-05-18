import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useLocation } from 'react-router-dom';
import { useSources, useCreateSource, useDeleteSource, useAlerts } from '../hooks/useDetection';
import AlertList from '../components/AlertList';
import { useAuth } from '../context/AuthContext';
import { PageHeader, Card, LiveIndicator, FilterBar, normalizeSeverity } from '../components/ui';
import { SHORTCUT_EVENTS } from '../hooks/useKeyboardShortcuts';

interface SourceFormData {
  name: string;
  source_value: string;
  source_type: 'reddit' | 'rss' | 'url';
  keywords: string;
  check_interval: number;
}

function normalizeRedditInput(value: string): string {
  const trimmed = value.trim();
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    const match = trimmed.match(/reddit\.com\/r\/([A-Za-z0-9_]+)/i);
    return match?.[1] ?? '';
  }
  if (trimmed.toLowerCase().startsWith('r/')) {
    return trimmed.slice(2).trim();
  }
  return trimmed;
}

const Monitoring: React.FC = () => {
  const [showForm, setShowForm] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [sourceFilter, setSourceFilter] = useState<string>('');
  const [searchFilter, setSearchFilter] = useState<string>('');
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const { data: sources, isLoading: sourcesLoading } = useSources();
  const { data: alerts, isLoading: alertsLoading, dataUpdatedAt: alertsUpdatedAt } = useAlerts();
  const createMutation = useCreateSource();
  const deleteMutation = useDeleteSource();
  const location = useLocation();
  const searchInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handler = () => searchInputRef.current?.focus();
    window.addEventListener(SHORTCUT_EVENTS.focusSearch, handler);
    return () => window.removeEventListener(SHORTCUT_EVENTS.focusSearch, handler);
  }, []);

  // Drill-through: accept `?severity=` and `?source=` from URL on mount.
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const sev = params.get('severity');
    const src = params.get('source');
    if (sev) setSeverityFilter(sev);
    if (src) setSourceFilter(src);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filteredAlerts = useMemo(() => {
    const list = alerts ?? [];
    const s = searchFilter.trim().toLowerCase();
    return list.filter((a) => {
      if (severityFilter && normalizeSeverity(a.threat_level) !== severityFilter) return false;
      if (sourceFilter && a.source_name !== sourceFilter) return false;
      if (s) {
        const hay = `${a.title} ${a.description ?? ''} ${a.source ?? ''}`.toLowerCase();
        if (!hay.includes(s)) return false;
      }
      return true;
    });
  }, [alerts, severityFilter, sourceFilter, searchFilter]);

  const sourceOptions = useMemo(
    () => (sources ?? []).map((s) => ({ value: s.name, label: s.name })),
    [sources],
  );

  const { register, handleSubmit, reset, watch, formState: { errors } } = useForm<SourceFormData>({
    defaultValues: {
      source_type: 'url',
      source_value: '',
      check_interval: 300,
    },
  });

  const sourceType = watch('source_type');

  const onSubmit = async (data: SourceFormData) => {
    if (isAdmin) return;

    const normalizedValue =
      data.source_type === 'reddit'
        ? normalizeRedditInput(data.source_value)
        : data.source_value.trim();

    await createMutation.mutateAsync({
      name: data.name,
      url: normalizedValue,
      source_type: data.source_type,
      keywords: data.keywords ? data.keywords.split(',').map((k) => k.trim()).filter(Boolean) : [],
      check_interval: data.check_interval,
    });
    reset();
    setShowForm(false);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Monitoring Sources"
        subtitle={
          <>
            <span>Manage your monitored feeds and review triggered alerts</span>
            <LiveIndicator dataUpdatedAt={alertsUpdatedAt} />
          </>
        }
        actions={
          !isAdmin ? (
            <button
              onClick={() => setShowForm(!showForm)}
              className="h-9 px-3 text-sm font-medium bg-primary-600 hover:bg-primary-700 text-white rounded-md"
            >
              {showForm ? 'Cancel' : '+ Add Source'}
            </button>
          ) : null
        }
      />

      {/* Monitoring Sources */}
      <div className="bg-panel rounded-lg border border-edge p-6">
        {isAdmin && (
          <div className="mb-4 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            Admin cannot add monitoring sources from this page.
          </div>
        )}

        {showForm && !isAdmin && (
          <form onSubmit={handleSubmit(onSubmit)} className="mb-6 p-4 bg-panel-alt rounded-lg space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Name</label>
                <input
                  {...register('name', { required: 'Name is required' })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
                {errors.name && <p className="text-red-500 text-xs mt-1">{errors.name.message}</p>}
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Type</label>
                <select
                  {...register('source_type')}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="reddit">Reddit</option>
                  <option value="rss">RSS Feed</option>
                  <option value="url">Website</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  {sourceType === 'reddit' ? 'Subreddit' : sourceType === 'rss' ? 'Feed URL' : 'Website URL'}
                </label>
                <input
                  {...register('source_value', {
                    required:
                      sourceType === 'reddit'
                        ? 'Subreddit is required'
                        : sourceType === 'rss'
                        ? 'RSS feed URL is required'
                        : 'Website URL is required',
                    validate: (value) => {
                      const v = value.trim();
                      if (!v) return 'Value is required';
                      if (sourceType === 'reddit') {
                        const sub = normalizeRedditInput(v);
                        return /^[A-Za-z0-9_]{2,21}$/.test(sub)
                          ? true
                          : 'Use subreddit name (e.g., worldnews) or a valid /r/<name> URL';
                      }
                      return /^https?:\/\//i.test(v)
                        ? true
                        : 'Please provide a valid http/https URL';
                    },
                  })}
                  type={sourceType === 'reddit' ? 'text' : 'url'}
                  placeholder={
                    sourceType === 'reddit'
                      ? 'e.g., worldnews or https://www.reddit.com/r/worldnews/'
                      : sourceType === 'rss'
                      ? 'e.g., https://example.com/feed.xml'
                      : 'e.g., https://example.com/news'
                  }
                  className="w-full px-3 py-2 border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
                {errors.source_value && <p className="text-red-500 text-xs mt-1">{errors.source_value.message}</p>}
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Check Interval (seconds)
                </label>
                <input
                  {...register('check_interval', { valueAsNumber: true, min: 60, max: 86400 })}
                  type="number"
                  className="w-full px-3 py-2 border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Keywords (comma-separated)
              </label>
              <input
                {...register('keywords')}
                placeholder="e.g., security, threat, extremism"
                className="w-full px-3 py-2 border border-slate-300 rounded-md bg-white text-slate-900 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <button
              type="submit"
              disabled={createMutation.isLoading}
              className="bg-primary-600 text-white py-2 px-4 rounded-md hover:bg-primary-700 disabled:opacity-50 font-medium"
            >
              {createMutation.isLoading ? 'Adding...' : 'Add Source'}
            </button>
          </form>
        )}

        {sourcesLoading ? (
          <p className="text-slate-500">Loading sources...</p>
        ) : sources && sources.length > 0 ? (
          <div className="space-y-3">
            {sources.map((source) => (
              <div
                key={source.id}
                className="flex items-center justify-between p-4 border border-edge rounded-lg hover:bg-panel-hover"
              >
                <div>
                  <h4 className="font-medium text-slate-900">{source.name}</h4>
                  <p className="text-sm text-slate-500 truncate max-w-md">{source.url}</p>
                  <div className="flex gap-2 mt-1">
                    <span className="text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded">{source.source_type}</span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${
                        source.is_active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'
                      }`}
                    >
                      {source.is_active ? 'Active' : 'Inactive'}
                    </span>
                    {source.keywords && source.keywords.length > 0 && (
                      <span className="text-xs text-slate-500">
                        {source.keywords.length} keywords
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => deleteMutation.mutate(source.id)}
                  className="text-red-500 hover:text-red-700 text-sm font-medium"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-slate-500">
            {isAdmin
              ? 'No user-owned monitoring sources assigned to this admin account.'
              : 'No monitoring sources configured yet. Add your first source after account activation.'}
          </p>
        )}
      </div>

      {/* Alerts */}
      <Card
        title={
          <span className="flex items-center gap-3">
            Alerts
            <LiveIndicator dataUpdatedAt={alertsUpdatedAt} />
          </span>
        }
      >
        <FilterBar
          severity={severityFilter}
          source={sourceFilter}
          search={searchFilter}
          onSeverityChange={setSeverityFilter}
          onSourceChange={setSourceFilter}
          onSearchChange={setSearchFilter}
          sourceOptions={sourceOptions}
          searchInputRef={searchInputRef}
          className="mb-3"
        />
        <AlertList alerts={filteredAlerts} loading={alertsLoading} />
      </Card>
    </div>
  );
};

export default Monitoring;
