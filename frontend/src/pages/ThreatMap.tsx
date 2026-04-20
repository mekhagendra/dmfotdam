import React from 'react';

const ThreatMap: React.FC = () => {
  return (
    <div className="dark-dashboard">
      <div
        style={{
          background: 'var(--bg1)',
          border: '1px solid var(--bdr)',
          borderRadius: 10,
          padding: '48px 32px',
          maxWidth: 420,
          margin: '80px auto',
          textAlign: 'center',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 16,
        }}
      >
        {/* Globe icon */}
        <svg
          width={32}
          height={32}
          viewBox="0 0 32 32"
          fill="none"
          stroke="var(--c3)"
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx={16} cy={16} r={14} />
          <ellipse cx={16} cy={16} rx={7} ry={14} />
          <line x1={2} y1={16} x2={30} y2={16} />
          <path d="M4.5 8.5h23M4.5 23.5h23" />
        </svg>

        {/* Heading */}
        <h2
          style={{
            fontSize: 20,
            fontWeight: 500,
            color: 'var(--txt)',
            margin: 0,
          }}
        >
          Threat map
        </h2>

        {/* Subtext */}
        <p
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 12,
            color: 'var(--txt3)',
            margin: 0,
          }}
        >
          Geographic threat distribution — coming soon
        </p>

        {/* Status badge */}
        <span
          style={{
            background: 'rgba(61,159,255,0.1)',
            border: '1px solid rgba(61,159,255,0.25)',
            borderRadius: 20,
            padding: '4px 14px',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 10,
            color: 'var(--c3)',
            letterSpacing: '0.06em',
          }}
        >
          IN DEVELOPMENT
        </span>
      </div>
    </div>
  );
};

export default ThreatMap;
