const TZ = 'Australia/Sydney';

export function formatDateTime(value: string | Date): string {
  return new Date(value).toLocaleString('en-AU', { timeZone: TZ });
}

export function formatDate(value: string | Date): string {
  return new Date(value).toLocaleDateString('en-AU', { timeZone: TZ });
}
