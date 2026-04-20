/**
 * highlightKeywords — wraps every occurrence of `keywords` inside `text`
 * with a <mark> tag for visual emphasis in JSX.
 *
 * Returns an array of React nodes (string | JSX.Element).
 */
import React from 'react';

export function highlightKeywords(
  text: string,
  keywords: string[],
): Array<string | React.ReactElement> {
  if (!keywords.length || !text) return [text];

  // Escape regex special chars and build alternation
  const escaped = keywords.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const pattern = new RegExp(`(${escaped.join('|')})`, 'gi');

  const parts = text.split(pattern);
  const lowerKeywords = new Set(keywords.map((k) => k.toLowerCase()));

  return parts.map((part, i) => {
    if (lowerKeywords.has(part.toLowerCase())) {
      return React.createElement(
        'mark',
        { key: i, className: 'bg-yellow-200 rounded px-0.5' },
        part,
      );
    }
    return part;
  });
}
