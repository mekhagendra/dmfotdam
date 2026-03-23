import api from './api';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  full_name?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserProfile {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  role: string;
}

export const authService = {
  async login(data: LoginRequest): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>('/auth/login', data);
    localStorage.setItem('access_token', response.data.access_token);
    return response.data;
  },

  async register(data: RegisterRequest): Promise<UserProfile> {
    const response = await api.post<UserProfile>('/auth/register', data);
    return response.data;
  },

  async getProfile(): Promise<UserProfile> {
    const response = await api.get<UserProfile>('/auth/me');
    return response.data;
  },

  logout(): void {
    localStorage.removeItem('access_token');
  },

  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
  },
};
