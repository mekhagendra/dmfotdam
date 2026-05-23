import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { authService } from '../services/auth.service';
import { GoogleLogin, CredentialResponse } from '@react-oauth/google';
import { toast } from 'react-toastify';

type Step = 'login' | 'login-otp' | 'register-form' | 'otp-verify' | 'forgot-password';

const Login: React.FC = () => {
  const [step, setStep] = useState<Step>('login');

  // shared
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');

  // OTP
  const [otp, setOtp] = useState('');
  const [loginOtp, setLoginOtp] = useState('');
  const [resetOtp, setResetOtp] = useState('');
  const [resetPassword, setResetPassword] = useState('');
  const [confirmResetPassword, setConfirmResetPassword] = useState('');
  const [resetOtpSent, setResetOtpSent] = useState(false);

  const [loading, setLoading] = useState(false);
  const { user, login, loginVerifyOtp, googleLogin, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();

  // Redirect if already authenticated
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      if (user?.role === 'admin') {
        navigate('/admin/users', { replace: true });
      } else {
        navigate('/', { replace: true });
      }
    }
  }, [isAuthenticated, isLoading, navigate, user]);

  // ---------- Login ----------
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const result = await login(username, password);
      if (result.kind === 'otp_required') {
        setLoginOtp('');
        setStep('login-otp');
        toast.info('Verification code sent to your email');
      } else if (result.user.role === 'admin') {
        navigate('/admin/users');
      } else {
        navigate('/');
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleLoginVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const profile = await loginVerifyOtp(username, loginOtp);
      setLoginOtp('');
      if (profile.role === 'admin') {
        navigate('/admin/users');
      } else {
        navigate('/');
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'OTP verification failed');
    } finally {
      setLoading(false);
    }
  };

  const handleResendLoginOtp = async () => {
    setLoading(true);
    try {
      await login(username, password);
      toast.success('New code sent');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Could not resend code');
    } finally {
      setLoading(false);
    }
  };

  // ---------- Register step 1: send OTP ----------
  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await authService.sendOtp({ email, username });
      toast.success('Verification code sent — check your email');
      setStep('otp-verify');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Could not send OTP');
    } finally {
      setLoading(false);
    }
  };

  // ---------- Register step 2: verify OTP & create account ----------
  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await authService.verifyOtpAndRegister({
        email,
        otp,
        username,
        password,
        full_name: fullName || undefined,
      });
      toast.success('Account created. Waiting for admin approval before login.');
      setStep('login');
      setOtp('');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Verification failed');
    } finally {
      setLoading(false);
    }
  };

  const resetForgotPasswordState = () => {
    setResetOtp('');
    setResetPassword('');
    setConfirmResetPassword('');
    setResetOtpSent(false);
  };

  const handleSendPasswordResetOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await authService.sendPasswordResetOtp({ email });
      toast.success(response.message || 'If the account exists, a reset code has been sent');
      setResetOtpSent(true);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Could not send reset code');
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (resetPassword !== confirmResetPassword) {
      toast.error('New password and confirm password must match');
      return;
    }
    setLoading(true);
    try {
      const response = await authService.resetPassword({
        email,
        otp: resetOtp,
        new_password: resetPassword,
      });
      toast.success(response.message || 'Password updated successfully');
      resetForgotPasswordState();
      setStep('login');
      setPassword('');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Could not reset password');
    } finally {
      setLoading(false);
    }
  };

  // ---------- Google ----------
  const handleGoogleSuccess = async (res: CredentialResponse) => {
    if (!res.credential) return;
    setLoading(true);
    try {
      const profile = await googleLogin(res.credential);
      if (profile.role === 'admin') {
        navigate('/admin/users');
      } else {
        navigate('/');
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Google sign-in failed');
    } finally {
      setLoading(false);
    }
  };

  // ---------- UI ----------
  const inputClass =
    'w-full px-3 py-2 border border-edge rounded-md bg-white text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-300 transition-colors';

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4 py-8"
      style={{
        background: 'linear-gradient(180deg, #F8FAFC 0%, #EEF2FF 100%)',
      }}
    >
      <div className="max-w-md w-full bg-panel rounded-xl border border-edge shadow-sm p-6 sm:p-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-slate-900">TDM System</h1>
          <p className="text-slate-600 mt-2">Terrorism Detection &amp; Monitoring</p>
        </div>

        {/* ============ LOGIN ============ */}
        {step === 'login' && (
          <>
            <h2 className="text-xl font-semibold mb-6 text-slate-900">Sign In</h2>

            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Username</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className={inputClass}
                  required
                  minLength={3}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={inputClass}
                  required
                  minLength={6}
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-primary-600 text-white py-2 px-4 rounded-md hover:bg-primary-700 disabled:opacity-50 font-medium"
              >
                {loading ? 'Please wait...' : 'Sign In'}
              </button>
            </form>

            <div className="mt-3 text-right">
              <button
                type="button"
                onClick={() => {
                  resetForgotPasswordState();
                  setEmail('');
                  setStep('forgot-password');
                }}
                className="text-primary-600 hover:text-primary-700 text-sm"
              >
                Forgot password?
              </button>
            </div>

            {/* Divider */}
            <div className="flex items-center my-5">
              <div className="flex-1 border-t border-edge" />
              <span className="mx-3 text-sm text-slate-500">or</span>
              <div className="flex-1 border-t border-edge" />
            </div>

            {/* Google sign-in */}
            <div className="flex justify-center">
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={() => toast.error('Google sign-in failed')}
                text="continue_with"
                shape="rectangular"
                width="360"
              />
            </div>

            <div className="mt-5 text-center">
              <button
                onClick={() => setStep('register-form')}
                className="text-primary-600 hover:text-primary-700 text-sm"
              >
                Don&apos;t have an account? Register
              </button>
            </div>
          </>
        )}

        {/* ============ LOGIN OTP ============ */}
        {step === 'login-otp' && (
          <>
            <h2 className="text-xl font-semibold mb-2 text-slate-900">Verify Sign-In</h2>
            <p className="text-sm text-slate-500 mb-6">
              Enter the 6-digit code we just emailed to the address on file for <strong>{username}</strong>.
            </p>

            <form onSubmit={handleLoginVerifyOtp} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Verification Code
                </label>
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={loginOtp}
                  onChange={(e) => setLoginOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  className={`${inputClass} text-center text-2xl tracking-[0.5em] font-mono`}
                  required
                  autoFocus
                />
              </div>
              <button
                type="submit"
                disabled={loading || loginOtp.length < 6}
                className="w-full bg-primary-600 text-white py-2 px-4 rounded-md hover:bg-primary-700 disabled:opacity-50 font-medium"
              >
                {loading ? 'Verifying...' : 'Verify & Sign In'}
              </button>
            </form>

            <div className="mt-4 flex justify-between text-sm">
              <button
                onClick={() => {
                  setLoginOtp('');
                  setStep('login');
                }}
                className="text-slate-500 hover:text-slate-700"
                disabled={loading}
              >
                &larr; Back
              </button>
              <button
                onClick={handleResendLoginOtp}
                disabled={loading}
                className="text-primary-600 hover:text-primary-700 disabled:opacity-50"
              >
                Resend code
              </button>
            </div>
          </>
        )}

        {/* ============ REGISTER — form ============ */}
        {step === 'register-form' && (
          <>
            <h2 className="text-xl font-semibold mb-6 text-slate-900">Create Account</h2>

            <form onSubmit={handleSendOtp} className="space-y-4">

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Full Name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className={inputClass}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={inputClass}
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Username</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className={inputClass}
                  required
                  minLength={3}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={inputClass}
                  required
                  minLength={8}
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-primary-600 text-white py-2 px-4 rounded-md hover:bg-primary-700 disabled:opacity-50 font-medium"
              >
                {loading ? 'Sending OTP...' : 'Send Verification Code'}
              </button>
            </form>

            {/* Divider */}
            <div className="flex items-center my-5">
              <div className="flex-1 border-t border-edge" />
              <span className="mx-3 text-sm text-slate-500">or</span>
              <div className="flex-1 border-t border-edge" />
            </div>

            {/* Google sign-up */}
            <div className="flex justify-center">
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={() => toast.error('Google sign-in failed')}
                text="signup_with"
                shape="rectangular"
                width="360"
              />
            </div>

            <div className="mt-5 text-center">
              <button
                onClick={() => setStep('login')}
                className="text-primary-600 hover:text-primary-700 text-sm"
              >
                Already have an account? Sign in
              </button>
            </div>
          </>
        )}

        {/* ============ OTP VERIFICATION ============ */}
        {step === 'otp-verify' && (
          <>
            <h2 className="text-xl font-semibold mb-2 text-slate-900">Verify Your Email</h2>
            <p className="text-sm text-slate-500 mb-6">
              Enter the 6-digit code we sent to <strong>{email}</strong>
            </p>

            <form onSubmit={handleVerifyOtp} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Verification Code
                </label>
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  className={`${inputClass} text-center text-2xl tracking-[0.5em] font-mono`}
                  required
                  autoFocus
                />
              </div>
              <button
                type="submit"
                disabled={loading || otp.length < 6}
                className="w-full bg-primary-600 text-white py-2 px-4 rounded-md hover:bg-primary-700 disabled:opacity-50 font-medium"
              >
                {loading ? 'Verifying...' : 'Verify & Create Account'}
              </button>
            </form>

            <div className="mt-4 flex justify-between text-sm">
              <button
                onClick={() => setStep('register-form')}
                className="text-slate-500 hover:text-slate-700"
              >
                &larr; Back
              </button>
              <button
                onClick={async () => {
                  try {
                    await authService.sendOtp({ email, username });
                    toast.success('New code sent');
                  } catch (err: any) {
                    toast.error(err.response?.data?.detail || 'Could not resend');
                  }
                }}
                className="text-primary-600 hover:text-primary-700"
              >
                Resend code
              </button>
            </div>
          </>
        )}

        {step === 'forgot-password' && (
          <>
            <h2 className="text-xl font-semibold mb-2 text-slate-900">Reset Password</h2>
            <p className="text-sm text-slate-500 mb-6">
              Enter your account email. We&apos;ll send a 6-digit OTP that lets you set a new password.
            </p>

            <form onSubmit={resetOtpSent ? handleResetPassword : handleSendPasswordResetOtp} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={inputClass}
                  required
                />
              </div>

              {resetOtpSent && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">OTP Code</label>
                    <input
                      type="text"
                      inputMode="numeric"
                      maxLength={6}
                      value={resetOtp}
                      onChange={(e) => setResetOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      className={`${inputClass} text-center text-2xl tracking-[0.5em] font-mono`}
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">New Password</label>
                    <input
                      type="password"
                      value={resetPassword}
                      onChange={(e) => setResetPassword(e.target.value)}
                      className={inputClass}
                      required
                      minLength={8}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Confirm New Password</label>
                    <input
                      type="password"
                      value={confirmResetPassword}
                      onChange={(e) => setConfirmResetPassword(e.target.value)}
                      className={inputClass}
                      required
                      minLength={8}
                    />
                  </div>
                </>
              )}

              <button
                type="submit"
                disabled={loading || (resetOtpSent && (resetOtp.length < 6 || resetPassword.length < 8 || confirmResetPassword.length < 8))}
                className="w-full bg-primary-600 text-white py-2 px-4 rounded-md hover:bg-primary-700 disabled:opacity-50 font-medium"
              >
                {loading ? 'Please wait...' : resetOtpSent ? 'Verify OTP & Change Password' : 'Send Reset OTP'}
              </button>
            </form>

            <div className="mt-4 flex justify-between text-sm">
              <button
                onClick={() => {
                  resetForgotPasswordState();
                  setStep('login');
                }}
                className="text-slate-500 hover:text-slate-700"
              >
                &larr; Back to sign in
              </button>
              {resetOtpSent && (
                <button
                  onClick={async () => {
                    try {
                      const response = await authService.sendPasswordResetOtp({ email });
                      toast.success(response.message || 'A new reset code has been sent');
                    } catch (err: any) {
                      toast.error(err.response?.data?.detail || 'Could not resend reset code');
                    }
                  }}
                  className="text-primary-600 hover:text-primary-700"
                >
                  Resend code
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default Login;
