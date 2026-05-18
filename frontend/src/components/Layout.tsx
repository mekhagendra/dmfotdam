import React, { useState, useEffect, useRef } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useUnreadAlertCount } from '../hooks/useDetection';
import { useDensity } from '../context/DensityContext';
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts';
import ShortcutsModal from './ShortcutsModal';
import { SHORTCUT_EVENTS } from '../hooks/useKeyboardShortcuts';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const { data: unreadCount = 0 } = useUnreadAlertCount();
  const [dropdownOpen, setDropdownOpen] = useState<boolean>(false);
  const [shortcutsOpen, setShortcutsOpen] = useState<boolean>(false);
  const [mobileNavOpen, setMobileNavOpen] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const mobileNavRef = useRef<HTMLDivElement>(null);
  const { density, toggle: toggleDensity } = useDensity();
  useKeyboardShortcuts();

  // Close mobile nav when route changes
  useEffect(() => {
    setMobileNavOpen(false);
  }, [location.pathname]);

  // Close mobile nav on outside click
  useEffect(() => {
    if (!mobileNavOpen) return;
    const handler = (e: MouseEvent) => {
      if (mobileNavRef.current && !mobileNavRef.current.contains(e.target as Node)) {
        setMobileNavOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [mobileNavOpen]);

  useEffect(() => {
    const handler = () => setShortcutsOpen(true);
    window.addEventListener(SHORTCUT_EVENTS.openShortcuts, handler);
    return () => window.removeEventListener(SHORTCUT_EVENTS.openShortcuts, handler);
  }, []);

  const primaryLinks = [
    { path: '/', label: 'Overview' },
    { path: '/analyse', label: 'Scan' },
    { path: '/monitor', label: 'Monitor' },
    { path: '/trends', label: 'Trends' },
    { path: '/reports', label: 'Reports' },
    ...(user?.role === 'admin' ? [{ path: '/admin/users', label: 'Users' }] : []),
  ];

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const initials = (user?.username?.toUpperCase() ?? 'AN').slice(0, 2);
  const displayName = user?.username ?? 'user';

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Topbar */}
      <header className="bg-white border-b border-slate-200 px-3 sm:px-4 py-2 min-h-[64px] flex flex-row items-center gap-2 sm:gap-3 shadow-sm relative">
        {/* Mobile hamburger */}
        <button
          type="button"
          onClick={() => setMobileNavOpen((p) => !p)}
          aria-label="Toggle navigation"
          aria-expanded={mobileNavOpen}
          className="lg:hidden inline-flex items-center justify-center w-9 h-9 rounded-md border border-slate-200 bg-white hover:bg-slate-50"
        >
          <svg width={18} height={18} viewBox="0 0 18 18" fill="none" stroke="#334155" strokeWidth={2} strokeLinecap="round">
            {mobileNavOpen ? (
              <>
                <line x1={4} y1={4} x2={14} y2={14} />
                <line x1={14} y1={4} x2={4} y2={14} />
              </>
            ) : (
              <>
                <line x1={3} y1={5} x2={15} y2={5} />
                <line x1={3} y1={9} x2={15} y2={9} />
                <line x1={3} y1={13} x2={15} y2={13} />
              </>
            )}
          </svg>
        </button>

        {/* Logo */}
        <Link
          to="/"
          className="flex items-center gap-2 sm:gap-3 no-underline lg:pr-3.5 lg:border-r lg:border-slate-200 min-w-0"
        >
          <img
            src="/logo.png"
            alt="TDM Logo"
            className="w-[34px] h-[34px] rounded-md object-contain flex-shrink-0"
          />
          <span className="hidden md:inline text-sm lg:text-base font-bold text-slate-800 tracking-wider leading-tight font-sans truncate">
            Threat Detection &amp; Monitoring System
          </span>
          <span className="md:hidden text-sm font-bold text-slate-800 tracking-wider">TDM</span>
        </Link>

        {/* Primary nav — desktop only (lg+) */}
        <nav className="hidden lg:flex flex-row items-center gap-1 px-2.5 overflow-x-auto">
          {primaryLinks.map((link) => {
            const active = location.pathname === link.path;
            return (
              <Link
                key={link.path}
                to={link.path}
                className={`text-[18px] font-extrabold tracking-wide min-h-[42px] whitespace-nowrap flex items-center border-b-2 no-underline transition-colors hover:text-primary-600 px-3 xl:px-4 ${
                  active
                    ? 'text-primary-600 border-primary-600'
                    : 'text-slate-700 border-transparent'
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Right utility zone */}
        <div className="flex flex-row items-center gap-2 sm:gap-4">
          {/* Density toggle */}
          <button
            type="button"
            onClick={toggleDensity}
            aria-label={`Switch to ${density === 'comfortable' ? 'compact' : 'comfortable'} density`}
            title={`Density: ${density}`}
            className="hidden md:inline-flex items-center gap-1 text-xs text-slate-600 hover:text-slate-900 border border-slate-200 rounded-full px-2 py-1 bg-slate-50 hover:bg-slate-100"
          >
            <span aria-hidden="true">{density === 'comfortable' ? '☰' : '≡'}</span>
            <span className="capitalize">{density}</span>
          </button>

          {/* Alerts bell */}
          <div className="relative">
            <button
              onClick={() => navigate('/monitoring')}
              aria-label="Alerts"
              className="bg-transparent border-0 p-1 cursor-pointer flex items-center rounded-md"
            >
              <svg
                width={18}
                height={18}
                viewBox="0 0 18 18"
                fill="none"
                stroke="#64748B"
                strokeWidth={1.5}
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x={4} y={2} width={10} height={11} rx={4} />
                <line x1={6.5} y1={15} x2={11.5} y2={15} />
                <line x1={9} y1={13} x2={9} y2={15} />
              </svg>
            </button>
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-1 min-w-[16px] h-4 rounded-full bg-red-500 border-2 border-white flex items-center justify-center font-mono text-[9px] font-semibold text-white px-[3px]">
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </div>

          {/* User chip */}
          <div className="relative" ref={dropdownRef}>
            <button
              type="button"
              onClick={() => setDropdownOpen((prev) => !prev)}
              aria-haspopup="menu"
              aria-expanded={dropdownOpen}
              className="flex flex-row items-center gap-2 px-3 py-1.5 border border-slate-200 rounded-full cursor-pointer bg-slate-50 hover:bg-slate-100 transition-colors"
            >
              <span className="w-6 h-6 rounded-full bg-blue-50 border border-blue-200 flex items-center justify-center text-[10px] font-semibold text-primary-600">
                {initials}
              </span>
              <span className="hidden sm:inline text-xs text-slate-600">{displayName}</span>
              <svg
                width={10}
                height={10}
                viewBox="0 0 10 10"
                fill="none"
                stroke="#94A3B8"
                strokeWidth={1.5}
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="2,3 5,7 8,3" />
              </svg>
            </button>

            {dropdownOpen && (
              <div
                role="menu"
                className="absolute top-11 right-0 z-50 bg-white border border-slate-200 rounded-lg py-1 min-w-[160px] shadow-md"
              >
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setDropdownOpen(false);
                    navigate('/monitoring');
                  }}
                  className="w-full text-left px-3.5 py-2 text-xs text-slate-600 cursor-pointer hover:bg-slate-50"
                >
                  Source Settings
                </button>
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setDropdownOpen(false);
                    navigate('/settings');
                  }}
                  className="w-full text-left px-3.5 py-2 text-xs text-slate-600 cursor-pointer hover:bg-slate-50"
                >
                  Settings
                </button>
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setDropdownOpen(false);
                    setShortcutsOpen(true);
                  }}
                  className="w-full text-left px-3.5 py-2 text-xs text-slate-600 cursor-pointer hover:bg-slate-50"
                >
                  ⌨ Shortcuts
                </button>
                <div className="h-px bg-slate-100 my-1" />
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setDropdownOpen(false);
                    logout();
                  }}
                  className="w-full text-left px-3.5 py-2 text-xs text-slate-600 cursor-pointer hover:bg-slate-50 hover:text-red-500"
                >
                  Sign Out
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Mobile nav drawer */}
        {mobileNavOpen && (
          <div
            ref={mobileNavRef}
            className="lg:hidden absolute top-full left-0 right-0 z-40 bg-white border-b border-slate-200 shadow-md"
          >
            <nav className="flex flex-col py-2">
              {primaryLinks.map((link) => {
                const active = location.pathname === link.path;
                return (
                  <Link
                    key={link.path}
                    to={link.path}
                    onClick={() => setMobileNavOpen(false)}
                    className={`px-4 py-3 text-base font-extrabold tracking-wide no-underline border-l-4 transition-colors ${
                      active
                        ? 'text-primary-600 border-primary-600 bg-blue-50'
                        : 'text-slate-700 border-transparent hover:bg-slate-50'
                    }`}
                  >
                    {link.label}
                  </Link>
                );
              })}
              <button
                type="button"
                onClick={() => {
                  toggleDensity();
                  setMobileNavOpen(false);
                }}
                className="md:hidden mx-4 mt-2 mb-1 inline-flex items-center justify-center gap-2 text-xs text-slate-600 border border-slate-200 rounded-full px-3 py-1.5 bg-slate-50 hover:bg-slate-100"
              >
                <span aria-hidden="true">{density === 'comfortable' ? '☰' : '≡'}</span>
                <span className="capitalize">Density: {density}</span>
              </button>
            </nav>
          </div>
        )}
      </header>

      {/* Main content */}
      <main className="bg-slate-50 min-h-[calc(100vh-64px)] p-3 md:px-5 md:py-4 lg:px-7">
        {children}
      </main>

      <ShortcutsModal open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
    </div>
  );
};

export default Layout;
