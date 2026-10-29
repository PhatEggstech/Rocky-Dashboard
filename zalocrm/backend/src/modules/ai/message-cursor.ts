// SPDX-License-Identifier: AGPL-3.0-or-later
export function decodeMessageCursor(value: string): { id: string; sentAt: Date } | null {
  if (value.length > 512) return null;
  try {
    const parsed = JSON.parse(Buffer.from(value, 'base64url').toString('utf8')) as { id?: unknown; sentAt?: unknown };
    if (typeof parsed.id !== 'string' || !parsed.id || parsed.id.length > 256 || typeof parsed.sentAt !== 'string') return null;
    const sentAt = new Date(parsed.sentAt);
    if (Number.isNaN(sentAt.getTime()) || sentAt.toISOString() !== parsed.sentAt) return null;
    return { id: parsed.id, sentAt };
  } catch { return null; }
}

export function encodeMessageCursor(value: { id: string; sentAt: Date }): string {
  return Buffer.from(JSON.stringify({ id: value.id, sentAt: value.sentAt.toISOString() })).toString('base64url');
}
