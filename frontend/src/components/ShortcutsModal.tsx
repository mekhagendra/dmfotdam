import React, { useEffect } from 'react';

interface ShortcutsModalProps {
  open: boolean;
  onClose: () => void;
}

const SHORTCUTS: Array<{ keys: string[]; label: string }> = [
  { keys: ['g', 'o'], label: 'Go to Overview' },
  { keys: ['g', 's'], label: 'Go to Scan / Analyse' },
  { keys: ['g', 'm'], label: 'Go to Monitor' },
  { keys: ['g', 't'], label: 'Go to Trends' },
  { keys: ['g', 'r'], label: 'Go to Reports' },
  { keys: ['/'], label: 'Focus search' },
  { keys: ['?'], label: 'Show this dialog' },
];

const Kbd: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <kbd className="font-mono text-[11px] px-1.5 py-0.5 border border-slate-300 rounded bg-slate-50 text-slate-700 shadow-sm">
    {children}
  </kbd>
);

const ShortcutsModal: React.FC<ShortcutsModalProps> = ({ open, onClose }) => {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard shortcuts"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-lg border border-slate-200 max-w-md w-full p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-slate-900">Keyboard shortcuts</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 text-xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <ul className="space-y-2">
          {SHORTCUTS.map((s) => (
            <li key={s.label} className="flex items-center justify-between text-sm">
              <span className="text-slate-700">{s.label}</span>
              <span className="flex items-center gap-1">
                {s.keys.map((k, i) => (
                  <React.Fragment key={i}>
                    {i > 0 && <span className="text-slate-400 text-xs">then</span>}
                    <Kbd>{k}</Kbd>
                  </React.Fragment>
                ))}
              </span>
            </li>
          ))}
        </ul>
        <p className="text-xs text-slate-500 mt-4">
          Shortcuts are disabled while typing in inputs.
        </p>
      </div>
    </div>
  );
};

export default ShortcutsModal;
