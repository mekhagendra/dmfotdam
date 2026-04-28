import React from 'react';
import { useMutation, useQuery, useQueryClient } from 'react-query';
import { toast } from 'react-toastify';
import { usersService } from '../services/users.service';

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
      <div className="rounded-lg border border-edge bg-panel p-6 text-slate-300">
        Loading users...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">User Management</h1>
        <p className="text-slate-400 text-sm mt-1">Manage user roles and approval status.</p>
      </div>

      <div className="overflow-x-auto rounded-lg border border-edge bg-panel">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-900/60 text-slate-300">
            <tr>
              <th className="px-4 py-3 text-left">Username</th>
              <th className="px-4 py-3 text-left">Email</th>
              <th className="px-4 py-3 text-left">Role</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id} className="border-t border-edge text-slate-200">
                <td className="px-4 py-3">{user.username}</td>
                <td className="px-4 py-3">{user.email}</td>
                <td className="px-4 py-3">
                  <select
                    value={user.role}
                    onChange={(e) =>
                      updateMutation.mutate({
                        userId: user.id,
                        payload: { role: e.target.value as 'admin' | 'customer' },
                      })
                    }
                    className="rounded border border-slate-600 bg-slate-900 px-2 py-1"
                    disabled={updateMutation.isLoading}
                  >
                    <option value="admin">admin</option>
                    <option value="customer">customer</option>
                  </select>
                </td>
                <td className="px-4 py-3">
                  <select
                    value={user.status}
                    onChange={(e) =>
                      updateMutation.mutate({
                        userId: user.id,
                        payload: { status: e.target.value as 'pending' | 'active' },
                      })
                    }
                    className="rounded border border-slate-600 bg-slate-900 px-2 py-1"
                    disabled={updateMutation.isLoading}
                  >
                    <option value="pending">pending</option>
                    <option value="active">active</option>
                  </select>
                </td>
                <td className="px-4 py-3 text-slate-400">
                  {updateMutation.isLoading ? 'Saving...' : 'Ready'}
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-slate-400">
                  No users found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AdminUsers;
