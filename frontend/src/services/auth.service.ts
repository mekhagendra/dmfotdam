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

export interface OTPRequest {
  email: string;
  username: string;
}

export interface OTPRegisterRequest {
  email: string;
  otp: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface PasswordResetOTPRequest {
  email: string;
}

export interface PasswordResetConfirmRequest {
  email: string;
  otp: string;
  new_password: string;
}

export interface UserProfile {
  id: string;
  username: string;
  email: string;
  full_name: string | null;
  role: string;
  status: 'pending' | 'active';
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface LoginOtpRequiredResponse {
  otp_required: true;
  message?: string;
}

export interface LoginVerifyOtpRequest {
  username: string;
  otp: string;
}

export const authService = {
  /**
   * Step 1 of login. With the current backend the response is
   * `{ otp_required: true }` — no token is issued until the OTP is verified
   * via `loginVerifyOtp`. We still tolerate a legacy `TokenResponse` shape
   * in case the backend is downgraded.
   */
  async login(
    data: LoginRequest,
  ): Promise<TokenResponse | LoginOtpRequiredResponse> {
    const response = await api.post<TokenResponse | LoginOtpRequiredResponse>(
      '/auth/login',
      data,
    );
    if ('access_token' in response.data) {
      localStorage.setItem('access_token', response.data.access_token);
    }
    return response.data;
  },

  /** Step 2 of login — submit the OTP that was emailed and receive the JWT. */
  async loginVerifyOtp(data: LoginVerifyOtpRequest): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>(
      '/auth/login/verify-otp',
      data,
    );
    localStorage.setItem('access_token', response.data.access_token);
    return response.data;
  },

  async register(data: RegisterRequest): Promise<UserProfile> {
    const response = await api.post<UserProfile>('/auth/register', data);
    return response.data;
  },

  /** Step 1 — send OTP to email */
  async sendOtp(data: OTPRequest): Promise<{ message: string }> {
    const response = await api.post<{ message: string }>('/auth/send-otp', data);
    return response.data;
  },

  /** Step 2 — verify OTP and register in pending state */
  async verifyOtpAndRegister(data: OTPRegisterRequest): Promise<UserProfile> {
    const response = await api.post<UserProfile>('/auth/verify-otp-register', data);
    return response.data;
  },

  async sendPasswordResetOtp(data: PasswordResetOTPRequest): Promise<{ message: string }> {
    const response = await api.post<{ message: string }>('/auth/forgot-password/send-otp', data);
    return response.data;
  },

  async resetPassword(data: PasswordResetConfirmRequest): Promise<{ message: string }> {
    const response = await api.post<{ message: string }>('/auth/forgot-password/reset-password', data);
    return response.data;
  },

  /** Google one-tap / button — send Google credential to backend */
  async googleLogin(credential: string): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>('/auth/google', { credential });
    localStorage.setItem('access_token', response.data.access_token);
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
