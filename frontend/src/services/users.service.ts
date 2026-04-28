import api from './api';

export interface AdminUser {
  id: string;
  username: string;
  email: string;
  full_name: string | null;
  role: 'admin' | 'customer';
  status: 'pending' | 'active';
  is_active: boolean;
  created_at: string;
}

export interface AdminUserUpdateRequest {
  role?: 'admin' | 'customer';
  status?: 'pending' | 'active';
}

export const usersService = {
  async listUsers(): Promise<AdminUser[]> {
    const response = await api.get<AdminUser[]>('/users');
    return response.data;
  },

  async updateUser(userId: string, data: AdminUserUpdateRequest): Promise<AdminUser> {
    const response = await api.patch<AdminUser>(`/users/${userId}`, data);
    return response.data;
  },
};
