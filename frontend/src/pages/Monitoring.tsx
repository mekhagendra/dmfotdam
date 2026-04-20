import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useSources, useCreateSource, useDeleteSource, useAlerts } from '../hooks/useDetection';
import AlertList from '../components/AlertList';

interface SourceFormData {
  name: string;
  url: string;
  source_type: string;
  keywords: string;
  check_interval: number;
}

const Monitoring: React.FC = () => {
  const [showForm, setShowForm] = useState(false);
  const { data: sources, isLoading: sourcesLoading } = useSources();
  const { data: alerts, isLoading: alertsLoading } = useAlerts();
  const createMutation = useCreateSource();
  const deleteMutation = useDeleteSource();

  const { register, handleSubmit, reset, formState: { errors } } = useForm<SourceFormData>({
    defaultValues: {
      source_type: 'website',
      check_interval: 300,
    },
  });

  const onSubmit = async (data: SourceFormData) => {
    await createMutation.mutateAsync({
      name: data.name,
      url: data.url,
      source_type: data.source_type,
      keywords: data.keywords ? data.keywords.split(',').map((k) => k.trim()).filter(Boolean) : [],
      check_interval: data.check_interval,
    });
    reset();
    setShowForm(false);
  };

  return (
    <div className="space-y-6">
      {/* Monitoring Sources */}
      <div className="bg-panel rounded-lg border border-edge p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-slate-100">Monitoring Sources</h2>
          <button
            onClick={() => setShowForm(!showForm)}
            className="bg-primary-600 text-white py-2 px-4 rounded-md hover:bg-primary-700 text-sm font-medium"
          >
            {showForm ? 'Cancel' : '+ Add Source'}
          </button>
        </div>

        {showForm && (
          <form onSubmit={handleSubmit(onSubmit)} className="mb-6 p-4 bg-panel-alt rounded-lg space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Name</label>
                <input
                  {...register('name', { required: 'Name is required' })}
                  className="w-full px-3 py-2 border border-slate-600 rounded-md bg-panel text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
                {errors.name && <p className="text-red-500 text-xs mt-1">{errors.name.message}</p>}
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">URL</label>
                <input
                  {...register('url', { required: 'URL is required' })}
                  type="url"
                  className="w-full px-3 py-2 border border-slate-600 rounded-md bg-panel text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
                {errors.url && <p className="text-red-500 text-xs mt-1">{errors.url.message}</p>}
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Type</label>
                <select
                  {...register('source_type')}
                  className="w-full px-3 py-2 border border-slate-600 rounded-md bg-panel text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="website">Website</option>
                  <option value="rss">RSS Feed</option>
                  <option value="social_media">Social Media</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Check Interval (seconds)
                </label>
                <input
                  {...register('check_interval', { valueAsNumber: true, min: 60, max: 86400 })}
                  type="number"
                  className="w-full px-3 py-2 border border-slate-600 rounded-md bg-panel text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Keywords (comma-separated)
              </label>
              <input
                {...register('keywords')}
                placeholder="e.g., security, threat, extremism"
                className="w-full px-3 py-2 border border-slate-600 rounded-md bg-panel text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
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
                  <h4 className="font-medium text-slate-200">{source.name}</h4>
                  <p className="text-sm text-slate-500 truncate max-w-md">{source.url}</p>
                  <div className="flex gap-2 mt-1">
                    <span className="text-xs bg-slate-700/50 text-slate-300 px-2 py-0.5 rounded">{source.source_type}</span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${
                        source.is_active ? 'bg-green-500/15 text-green-400' : 'bg-slate-700/50 text-slate-500'
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
          <p className="text-slate-500">No monitoring sources configured.</p>
        )}
      </div>

      {/* Alerts */}
      <div className="bg-panel rounded-lg border border-edge p-6">
        <h2 className="text-xl font-semibold mb-4 text-slate-100">Alerts</h2>
        <AlertList alerts={alerts ?? []} loading={alertsLoading} />
      </div>
    </div>
  );
};

export default Monitoring;
