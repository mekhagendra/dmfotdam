import React, { useState, useEffect, useRef } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useUnreadAlertCount } from '../hooks/useDetection';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const { data: unreadCount = 0 } = useUnreadAlertCount();
  const [dropdownOpen, setDropdownOpen] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const primaryLinks = [
    { path: '/', label: 'overview' },
    { path: '/analyse', label: 'Scan' },
    { path: '/intel-feed', label: 'Threats' },
    { path: '/monitoring', label: 'Source' },
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
    <div style={{ minHeight: '100vh', background: '#F8FAFC' }}>
      {/* Topbar */}
      <header
        style={{
          background: '#FFFFFF',
          borderBottom: '1px solid #E2E8F0',
          padding: '0 32px',
          height: 64,
          display: 'flex',
          flexDirection: 'row',
          alignItems: 'stretch',
          boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
        }}
      >
        {/* Logo */}
        <Link
          to="/"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            paddingRight: 28,
            borderRight: '1px solid #E2E8F0',
            textDecoration: 'none',
          }}
        >
          <img
            src="/logo.png"
            alt="TDM Logo"
            style={{
              width: 34,
              height: 34,
              borderRadius: 6,
              objectFit: 'contain',
            }}
          />
          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            <span
              style={{
                fontSize: 16,
                fontWeight: 700,
                color: '#1E293B',
                letterSpacing: '0.05em',
                fontFamily: "'Space Grotesk', sans-serif",
                lineHeight: 1.2,
              }}
            >
              Threat Detection & Monitoring System
            </span>
          </div>
        </Link>

        {/* Primary nav links */}
        <nav
          style={{
            display: 'flex',
            flexDirection: 'row',
            alignItems: 'stretch',
            padding: '0 24px',
            gap: 4,
          }}
        >
          {primaryLinks.map((link) => {
            const active = location.pathname === link.path;
            return (
              <Link
                key={link.path}
                to={link.path}
                className="layout-nav-link"
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 13,
                  color: active ? '#2563EB' : '#64748B',
                  letterSpacing: '0.04em',
                  padding: '0 18px',
                  display: 'flex',
                  alignItems: 'center',
                  borderBottom: `2px solid ${active ? '#2563EB' : 'transparent'}`,
                  textDecoration: 'none',
                  transition: 'color 0.15s',
                  fontWeight: active ? 600 : 400,
                }}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Right utility zone */}
        <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', gap: 16 }}>
          {/* Alerts bell */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => navigate('/monitoring')}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: 4,
                display: 'flex',
                alignItems: 'center',
                borderRadius: 6,
              }}
              aria-label="Alerts"
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
              <span
                style={{
                  position: 'absolute',
                  top: -2,
                  right: -4,
                  minWidth: 16,
                  height: 16,
                  borderRadius: 8,
                  background: '#EF4444',
                  border: '2px solid #FFFFFF',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 9,
                  fontWeight: 600,
                  color: 'white',
                  padding: '0 3px',
                }}
              >
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </div>

          {/* User chip */}
          <div style={{ position: 'relative' }} ref={dropdownRef}>
            <div
              onClick={() => setDropdownOpen((prev) => !prev)}
              style={{
                display: 'flex',
                flexDirection: 'row',
                alignItems: 'center',
                gap: 8,
                padding: '6px 12px',
                border: '1px solid #E2E8F0',
                borderRadius: 20,
                cursor: 'pointer',
                background: '#F8FAFC',
              }}
            >
              {/* Avatar */}
              <div
                style={{
                  width: 24,
                  height: 24,
                  borderRadius: '50%',
                  background: '#EFF6FF',
                  border: '1px solid #BFDBFE',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 10,
                  fontWeight: 600,
                  color: '#2563EB',
                }}
              >
                {initials}
              </div>
              {/* Username */}
              <span
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 11,
                  color: '#475569',
                }}
              >
                {displayName}
              </span>
              {/* Chevron */}
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
            </div>

            {/* Dropdown menu */}
            {dropdownOpen && (
              <div
                style={{
                  position: 'absolute',
                  top: 44,
                  right: 0,
                  zIndex: 50,
                  background: '#FFFFFF',
                  border: '1px solid #E2E8F0',
                  borderRadius: 8,
                  padding: '4px 0',
                  minWidth: 160,
                  boxShadow: '0 4px 6px -1px rgba(0,0,0,0.08)',
                }}
              >
                <div
                  className="layout-dropdown-item"
                  onClick={() => {
                    setDropdownOpen(false);
                    navigate('/settings');
                  }}
                  style={{
                    padding: '8px 14px',
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 11,
                    color: '#475569',
                    cursor: 'pointer',
                  }}
                >
                  settings
                </div>
                <div
                  style={{
                    height: 1,
                    background: '#F1F5F9',
                    margin: '4px 0',
                  }}
                />
                <div
                  className="layout-dropdown-item layout-dropdown-signout"
                  onClick={() => {
                    setDropdownOpen(false);
                    logout();
                  }}
                  style={{
                    padding: '8px 14px',
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 11,
                    color: '#475569',
                    cursor: 'pointer',
                  }}
                >
                  sign out
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main content */}
      <main
        style={{
          background: '#F8FAFC',
          minHeight: 'calc(100vh - 64px)',
          padding: '20px 32px',
        }}
      >
        {children}
      </main>

      {/* Hover styles */}
      <style>{`
        .layout-nav-link:hover {
          color: #2563EB !important;
        }
        .layout-dropdown-item:hover {
          background: #F8FAFC;
        }
        .layout-dropdown-signout:hover {
          color: #EF4444 !important;
        }
      `}</style>
    </div>
  );
};

export default Layout;