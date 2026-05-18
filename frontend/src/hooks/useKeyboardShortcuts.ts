import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

/** Custom DOM event names emitted by global shortcuts. */
export const SHORTCUT_EVENTS = {
  focusSearch: 'tdm:focus-search',
  openShortcuts: 'tdm:open-shortcuts',
} as const;

/**
 * Global keyboard shortcuts. Mounted once near the app root.
 * Supports a two-key `g` chord (g+o / g+s / g+m / g+t / g+r) plus
 * `/` (focus FilterBar search) and `?` (open shortcuts modal).
 *
 * Shortcuts are suppressed while the user is typing in an input.
 */
export function useKeyboardShortcuts(): void {
  const navigate = useNavigate();

  useEffect(() => {
    let gPending = false;
    let gTimer: number | null = null;

    const clearG = () => {
      gPending = false;
      if (gTimer != null) {
        window.clearTimeout(gTimer);
        gTimer = null;
      }
    };

    const isTypingTarget = (target: EventTarget | null): boolean => {
      if (!(target instanceof HTMLElement)) return false;
      const tag = target.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
      if (target.isContentEditable) return true;
      return false;
    };

    const handler = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const typing = isTypingTarget(e.target);

      // "/" → focus search (allowed even when not typing; we suppress when typing).
      if (e.key === '/' && !typing) {
        e.preventDefault();
        window.dispatchEvent(new CustomEvent(SHORTCUT_EVENTS.focusSearch));
        return;
      }
      // "?" → open shortcuts modal.
      if (e.key === '?' && !typing) {
        e.preventDefault();
        window.dispatchEvent(new CustomEvent(SHORTCUT_EVENTS.openShortcuts));
        return;
      }
      if (typing) return;

      // "g" chord
      if (gPending) {
        const map: Record<string, string> = {
          o: '/',
          s: '/analyse',
          m: '/monitor',
          t: '/trends',
          r: '/reports',
        };
        const dest = map[e.key.toLowerCase()];
        if (dest) {
          e.preventDefault();
          navigate(dest);
        }
        clearG();
        return;
      }
      if (e.key.toLowerCase() === 'g') {
        gPending = true;
        gTimer = window.setTimeout(clearG, 1200);
      }
    };

    window.addEventListener('keydown', handler);
    return () => {
      window.removeEventListener('keydown', handler);
      clearG();
    };
  }, [navigate]);
}
