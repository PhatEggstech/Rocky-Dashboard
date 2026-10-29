import { describe, expect, it } from 'vitest';
import { decodeMessageCursor, encodeMessageCursor } from './message-cursor.js';

describe('message cursor', () => {
  it('retains both timestamp and ID for tied message times', () => {
    const original = { id: 'message-2', sentAt: new Date('2026-10-27T00:00:00.000Z') };
    expect(decodeMessageCursor(encodeMessageCursor(original))).toEqual(original);
  });
  it('rejects malformed, noncanonical and oversized cursors', () => {
    const token = (value: unknown) => Buffer.from(JSON.stringify(value)).toString('base64url');
    expect(decodeMessageCursor('bad')).toBeNull();
    expect(decodeMessageCursor('x'.repeat(513))).toBeNull();
    expect(decodeMessageCursor(token({ id: 'x', sentAt: '2026-10-27' }))).toBeNull();
    expect(decodeMessageCursor(token({ id: '', sentAt: '2026-10-27T00:00:00.000Z' }))).toBeNull();
  });
});
