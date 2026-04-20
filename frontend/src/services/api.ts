import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to attach auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Only logout on 401 if:
    // 1. There's actually a token (user was logged in)
    // 2. It's from the /auth/me endpoint (token validation)
    if (error.response?.status === 401) {
      const token = localStorage.getItem('access_token');
      const isAuthEndpoint = error.config?.url?.includes('/auth/me');
      
      // Only force logout if this is an auth validation failure
      if (token && isAuthEndpoint) {
        localStorage.removeItem('access_token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;
