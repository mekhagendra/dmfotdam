import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from 'react-query';
import { toast } from 'react-toastify';
import { usersService } from '../services/users.service';
import { useTrainModels, useTrainingStatus, useAvailableModels } from '../hooks/useDetection';
import { formatDateTime } from '../utils/formatDate';

const STATUS_COLOR: Record<string, { bg: string; color: string }> = {
  completed: { bg: '#DCFCE7', color: '#16A34A' },
  running: { bg: '#FEF9C3', color: '#CA8A04' },
  pending: { bg: '#FEF9C3', color: '#CA8A04' },
  failed: { bg: '#FEE2E2', color: '#DC2626' },
};

const ModelTrainingPanel: React.FC = () => {
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const trainMutation = useTrainModels();
  const { data: jobStatus } = useTrainingStatus(activeJobId);
  const { data: availableModels = [] } = useAvailableModels();

  const handleTrain = async () => {
    const result = await trainMutation.mutateAsync();
    if (result.job_id) setActiveJobId(result.job_id);
  };

  const statusInfo = jobStatus as any;
  const jobState: string = statusInfo?.status || '';
  const sc = STATUS_COLOR[jobState] || { bg: '#F1F5F9', color: '#475569' };

  return (
    <div style={{ background: '#FFFFFF', borderRadius: 12, border: '1px solid #E2E8F0', padding: 24, marginBottom: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 17, fontWeight: 700, color: '#1E293B', margin: 0 }}>ML Model Training</h2>
          <p style={{ fontSize: 13, color: '#64748B', marginTop: 4 }}>
            Train or retrain all ML models at once (SGD, Logistic Regression, Random Forest, Linear SVC). This runs in the background.
          </p>
        </div>
        <button
          onClick={handleTrain}
          disabled={trainMutation.isLoading || jobState === 'running' || jobState === 'pending'}
          style={{
            background: '#2563EB',
            color: '#FFFFFF',
            border: 'none',
            borderRadius: 8,
            padding: '10px 20px',
            fontWeight: 600,
            fontSize: 14,
            cursor: (trainMutation.isLoading || jobState === 'running' || jobState === 'pending') ? 'not-allowed' : 'pointer',
            opacity: (trainMutation.isLoading || jobState === 'running' || jobState === 'pending') ? 0.6 : 1,
            whiteSpace: 'nowrap',
          }}
        >
          {jobState === 'running' || jobState === 'pending' ? 'Training…' : 'Train All Models'}
        </button>
      </div>

      {/* Available models */}
      {availableModels.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <p style={{ fontSize: 12, color: '#94A3B8', marginBottom: 8 }}>Currently available models:</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {availableModels.map((m) => (
              <span key={m.id} style={{ background: '#EFF6FF', color: '#2563EB', borderRadius: 6, padding: '3px 12px', fontSize: 12, fontWeight: 500 }}>
                {m.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Job status */}
      {activeJobId && jobStatus && (
        <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 8, padding: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: jobState === 'completed' || jobState === 'failed' ? 8 : 0 }}>
            <span style={{ background: sc.bg, color: sc.color, borderRadius: 5, padding: '2px 10px', fontWeight: 600, fontSize: 12 }}>
              {jobState}
            </span>
            <span style={{ fontSize: 12, color: '#94A3B8' }}>Job: {activeJobId.slice(0, 12)}…</span>
            {statusInfo?.started_at && (
              <span style={{ fontSize: 12, color: '#94A3B8' }}>Started: {formatDateTime(statusInfo.started_at)}</span>
            )}
          </div>
          {jobState === 'running' && (
            <p style={{ fontSize: 12, color: '#CA8A04', margin: '6px 0 0' }}>Training in progress… this may take several minutes.</p>
          )}
          {jobState === 'completed' && (
            <p style={{ fontSize: 12, color: '#16A34A', margin: '6px 0 0' }}>All models trained successfully. Models have been reloaded.</p>
          )}
          {jobState === 'failed' && statusInfo?.error && (
            <pre style={{ fontSize: 11, color: '#DC2626', margin: '6px 0 0', whiteSpace: 'pre-wrap', maxHeight: 120, overflowY: 'auto', background: '#FEE2E2', borderRadius: 4, padding: 8 }}>
              {statusInfo.error}
            </pre>
          )}
        </div>
      )}
    </div>
  );
};

const AdminUsers: React.FC = () => {
  const queryClient = useQueryClient();

  const { data: users = [], isLoading } = useQuery('admin-users', usersService.listUsers);

  const updateMutation = useMutation(
    ({ userId, payload }: { userId: string; payload: { role?: 'admin' | 'customer'; status?: 'pending' | 'active' } }) =>
      usersService.updateUser(userId, payload),
    {
      onSuccess: () => {
        toast.success('User updated');
        queryClient.invalidateQueries('admin-users');
      },
      onError: (error: any) => {
        toast.error(error?.response?.data?.detail || 'Failed to update user');
      },
    }
  );

  if (isLoading) {
    return (
      <div style={{ borderRadius: 12, border: '1px solid #E2E8F0', background: '#FFFFFF', padding: 24, color: '#475569' }}>
        Loading users...
      </div>
    );
  }

  return (
    <div>
      {/* Model Training Panel — admin-only functionality */}
      <ModelTrainingPanel />

      {/* User Management */}
      <div style={{ background: '#FFFFFF', borderRadius: 12, border: '1px solid #E2E8F0', overflow: 'hidden' }}>
        <div style={{ padding: '20px 24px 16px', borderBottom: '1px solid #F1F5F9' }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: '#1E293B', margin: 0 }}>User Management</h1>
          <p style={{ fontSize: 13, color: '#64748B', marginTop: 4 }}>Manage user roles and approval status.</p>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#F8FAFC' }}>
                {['Username', 'Email', 'Role', 'Status', 'Actions'].map((h) => (
                  <th key={h} style={{ padding: '10px 16px', textAlign: 'left', color: '#64748B', fontWeight: 600, borderBottom: '2px solid #E2E8F0' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                  <td style={{ padding: '10px 16px', color: '#1E293B', fontWeight: 500 }}>{user.username}</td>
                  <td style={{ padding: '10px 16px', color: '#475569' }}>{user.email}</td>
                  <td style={{ padding: '10px 16px' }}>
                    <select
                      value={user.role}
                      onChange={(e) =>
                        updateMutation.mutate({
                          userId: user.id,
                          payload: { role: e.target.value as 'admin' | 'customer' },
                        })
                      }
                      disabled={updateMutation.isLoading}
                      style={{ borderRadius: 6, border: '1px solid #E2E8F0', background: '#F8FAFC', padding: '5px 10px', color: '#1E293B', fontSize: 13 }}
                    >
                      <option value="admin">admin</option>
                      <option value="customer">customer</option>
                    </select>
                  </td>
                  <td style={{ padding: '10px 16px' }}>
                    <select
                      value={user.status}
                      onChange={(e) =>
                        updateMutation.mutate({
                          userId: user.id,
                          payload: { status: e.target.value as 'pending' | 'active' },
                        })
                      }
                      disabled={updateMutation.isLoading}
                      style={{ borderRadius: 6, border: '1px solid #E2E8F0', background: '#F8FAFC', padding: '5px 10px', color: '#1E293B', fontSize: 13 }}
                    >
                      <option value="pending">pending</option>
                      <option value="active">active</option>
                    </select>
                  </td>
                  <td style={{ padding: '10px 16px', color: '#94A3B8', fontSize: 12 }}>
                    {updateMutation.isLoading ? 'Saving…' : 'Ready'}
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ padding: '24px 16px', textAlign: 'center', color: '#94A3B8' }}>
                    No users found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AdminUsers;
