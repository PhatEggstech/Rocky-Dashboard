// SPDX-License-Identifier: AGPL-3.0-or-later
// Classify only explicit source types; URLs and user text must not imply media.
const mediaTypes = new Set(['photo', 'image', 'sticker', 'document', 'video', 'audio', 'voice']);
const eventLabels: Record<string, string> = {
  pzl_chat_recommended: 'Sự kiện gợi ý liên hệ từ Pancake',
  pzl_new_friend_request: 'Sự kiện yêu cầu kết bạn',
  zalo_system_message: 'Sự kiện hệ thống Zalo',
  reaction: 'Tương tác với tin nhắn',
  replied_message: 'Tin nhắn trả lời',
  styled_message: 'Tin nhắn có định dạng',
  'chat.webcontent': 'Nội dung chia sẻ từ Zalo',
  address: 'Địa chỉ được chia sẻ',
  link: 'Liên kết được chia sẻ',
};

export function pancakeAttachmentDisplay(attachments: unknown): { hasMedia: boolean; label: string | null; hasKnownType: boolean; hasRecordedType: boolean } {
  if (!Array.isArray(attachments)) return { hasMedia: false, label: null, hasKnownType: false, hasRecordedType: false };
  const types = attachments.flatMap((item: unknown) => item && typeof item === 'object' && typeof (item as { type?: unknown }).type === 'string' ? [(item as { type: string }).type.toLowerCase()] : []);
  if (!types.length) return { hasMedia: false, label: null, hasKnownType: false, hasRecordedType: false };
  const hasNestedMedia = attachments.some((item: unknown) => {
    if (!item || typeof item !== 'object') return false;
    const record = item as { type?: unknown; attachments?: unknown };
    return record.type === 'replied_message' && Array.isArray(record.attachments)
      && record.attachments.some((nested: unknown) => nested && typeof nested === 'object'
        && typeof (nested as { type?: unknown }).type === 'string'
        && mediaTypes.has((nested as { type: string }).type.toLowerCase()));
  });
  const hasMedia = types.some((type) => mediaTypes.has(type)) || hasNestedMedia;
  const label = types.map((type) => eventLabels[type]).find(Boolean) ?? null;
  return { hasMedia, label, hasKnownType: types.some((type) => mediaTypes.has(type) || Boolean(eventLabels[type])), hasRecordedType: true };
}
