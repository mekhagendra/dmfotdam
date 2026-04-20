import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authService, UserProfile } from '../services/auth.service';

interface AuthContextType {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string, fullName?: string) => Promise<void>;
  googleLogin: (credential: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadUser = useCallback(async () => {
    if (authService.isAuthenticated()) {
      try {
        const profile = await authService.getProfile();
        setUser(profile);
      } catch (error: any) {
        // Only logout on actual authentication failure (401)
        // Don't logout on network errors or other temporary issues
        if (error?.response?.status === 401) {
          authService.logout();
          setUser(null);
        }
        // For other errors, keep the token and try again later
      }
    }
    setIsLoading(false);
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const login = async (username: string, password: string) => {
    await authService.login({ username, password });
    const profile = await authService.getProfile();
    setUser(profile);
  };

  const register = async (username: string, email: string, password: string, fullName?: string) => {
    await authService.register({ username, email, password, full_name: fullName });
  };

  const googleLogin = async (credential: string) => {
    const res = await authService.googleLogin(credential);
    setUser(res.user);
  };

  const logout = () => {
    authService.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        googleLogin,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
