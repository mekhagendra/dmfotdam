/**
 * Severity color mapping — single source of truth for the entire app.
 * Pair the color with text labels so color is never the only signal.
 */
export type SeverityLevel = 'critical' | 'high' | 'medium' | 'low';

export interface SeverityStyle {
  /** Background color for badges / tinted backgrounds */
  bg: string;
  /** Text color paired with the bg */
  text: string;
  /** Solid accent color (used for rails, dots, chart segments) */
  accent: string;
  /** Tailwind class shortcut for badge backgrounds */
  badgeClass: string;
  /** Tailwind class shortcut for the colored rail/dot */
  railClass: string;
}

export const SEVERITY_STYLES: Record<SeverityLevel, SeverityStyle> = {
  critical: {
    bg: '#FEE2E2',
    text: '#B91C1C',
    accent: '#EF4444',
    badgeClass: 'bg-[#FEE2E2] text-[#B91C1C]',
    railClass: 'bg-[#EF4444]',
  },
  high: {
    bg: '#FFEDD5',
    text: '#9A3412',
    accent: '#F97316',
    badgeClass: 'bg-[#FFEDD5] text-[#9A3412]',
    railClass: 'bg-[#F97316]',
  },
  medium: {
    bg: '#FEF9C3',
    text: '#854D0E',
    accent: '#EAB308',
    badgeClass: 'bg-[#FEF9C3] text-[#854D0E]',
    railClass: 'bg-[#EAB308]',
  },
  low: {
    bg: '#DBEAFE',
    text: '#1E40AF',
    accent: '#3B82F6',
    badgeClass: 'bg-[#DBEAFE] text-[#1E40AF]',
    railClass: 'bg-[#3B82F6]',
  },
};

/** Normalize an arbitrary severity string to a known level (fallback: 'low'). */
export function normalizeSeverity(level: string | null | undefined): SeverityLevel {
  if (!level) return 'low';
  const lower = level.toLowerCase();
  if (lower === 'critical' || lower === 'high' || lower === 'medium' || lower === 'low') {
    return lower;
  }
  return 'low';
}

/** Get the accent color for any severity string (safe fallback). */
export function severityAccent(level: string | null | undefined): string {
  return SEVERITY_STYLES[normalizeSeverity(level)].accent;
}
