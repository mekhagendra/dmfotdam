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
    <div style={{ minHeight: '100vh', background: '#060A12' }}>
      {/* Topbar */}
      <header
        style={{
          background: '#080E1A',
          borderBottom: '1px solid rgba(0,245,196,0.12)',
          padding: '0 32px',
          height: 64,
          display: 'flex',
          flexDirection: 'row',
          alignItems: 'stretch',
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
            borderRight: '1px solid rgba(0,245,196,0.12)',
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
                color: '#E8F0F8',
                letterSpacing: '0.05em',
                fontFamily: "'Space Grotesk', sans-serif",
                lineHeight: 1.2,
              }}
            >
              TDM
            </span>
            <span
              style={{
                fontSize: 11,
                fontFamily: "'JetBrains Mono', monospace",
                color: '#3D5A72',
                lineHeight: 1.2,
              }}
            >
              threat detection matrix
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
                  fontSize: 16,
                  color: active ? '#00F5C4' : '#3D5A72',
                  letterSpacing: '0.04em',
                  padding: '0 18px',
                  display: 'flex',
                  alignItems: 'center',
                  borderBottom: `2px solid ${active ? '#00F5C4' : 'transparent'}`,
                  textDecoration: 'none',
                  transition: 'color 0.15s',
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
                padding: 0,
                display: 'flex',
                alignItems: 'center',
              }}
              aria-label="Alerts"
            >
              <svg
                width={18}
                height={18}
                viewBox="0 0 18 18"
                fill="none"
                stroke="#3D5A72"
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
                  top: -4,
                  right: -6,
                  minWidth: 16,
                  height: 16,
                  borderRadius: 8,
                  background: '#FF4D6A',
                  border: '2px solid #080E1A',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 9,
                  fontWeight: 500,
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
                padding: '6px 10px',
                border: '1px solid rgba(0,245,196,0.2)',
                borderRadius: 20,
                cursor: 'pointer',
              }}
            >
              {/* Avatar */}
              <div
                style={{
                  width: 24,
                  height: 24,
                  borderRadius: '50%',
                  background: '#182030',
                  border: '1px solid rgba(61,159,255,0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 10,
                  fontWeight: 500,
                  color: '#3D9FFF',
                }}
              >
                {initials}
              </div>
              {/* Username */}
              <span
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 11,
                  color: '#7A9AB5',
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
                stroke="#3D5A72"
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
                  background: '#0C1220',
                  border: '1px solid rgba(0,245,196,0.15)',
                  borderRadius: 8,
                  padding: '4px 0',
                  minWidth: 160,
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
                    color: '#7A9AB5',
                    cursor: 'pointer',
                  }}
                >
                  settings
                </div>
                <div
                  style={{
                    height: 1,
                    background: 'rgba(0,245,196,0.08)',
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
                    color: '#7A9AB5',
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
          background: '#060A12',
          minHeight: 'calc(100vh - 64px)',
          padding: '20px 32px',
        }}
      >
        {children}
      </main>

      {/* Hover styles */}
      <style>{`
        .layout-nav-link:hover {
          color: #7A9AB5 !important;
        }
        .layout-dropdown-item:hover {
          background: rgba(0,245,196,0.06);
        }
        .layout-dropdown-signout:hover {
          color: #FF4D6A !important;
        }
      `}</style>
    </div>
  );
};

export default Layout;