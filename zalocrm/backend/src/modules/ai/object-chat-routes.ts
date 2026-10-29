// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * Read-only Object Chat workspace for imported conversation history.
 * AI writers use the adapter tables separately; this API never invokes a
 * model, mutates a message, or exposes source credentials/media URLs.
 */
import type { FastifyInstance, FastifyReply, FastifyRequest } from 'fastify';
import { prisma } from '../../shared/database/prisma-client.js';
import { authMiddleware } from '../auth/auth-middleware.js';
import { getZaloScope } from '../zalo/zalo-scope.js';
import { decodeMessageCursor, encodeMessageCursor } from './message-cursor.js';
import { runSystemQuery } from '../../shared/tenant/tenant-context.js';

function boundedLimit(value: unknown, fallback: number, maximum: number): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? Math.min(parsed, maximum) : fallback;
}

export async function objectChatRoutes(app: FastifyInstance) {
  app.addHook('preHandler', authMiddleware);

  app.get('/api/v1/object-chat/activity', async (request: FastifyRequest, reply: FastifyReply) => {
    const user = request.user!;
    const scope = await getZaloScope(user.id, user.orgId, user.role);
    const accountFilter = scope.isOrgAdmin ? {} : { zaloAccountId: { in: scope.displayableIds } };
    const topics = await prisma.rockyAiObject.findMany({
      where: { orgId: user.orgId, conversation: { orgId: user.orgId, deletedAt: null, ...accountFilter } },
      select: { id: true, naturalName: true, updatedAt: true, conversationId: true, conversation: { select: { groupName: true, contact: { select: { fullName: true } } } } },
      orderBy: [{ updatedAt: 'desc' }, { id: 'asc' }], take: 10,
    });
    // Rocky's counters are system-wide. Expose them only to an organization
    // administrator when all imported Rocky conversations belong to this org.
    let system: unknown = null;
    let systemAvailable = false;
    if (scope.isOrgAdmin) {
      // This is a cross-tenant safety check, not a business-data query: if
      // more than one organization has an import, never expose global stats.
      const owners = await runSystemQuery(() => prisma.rockyAiConversationAnalysis.findMany({ distinct: ['orgId'], select: { orgId: true }, take: 2 }));
      if (owners.length === 1 && owners[0].orgId === user.orgId) {
        try {
          const response = await fetch('http://host.docker.internal:18082/api/chat/v1/analysis/status', { signal: AbortSignal.timeout(5000) });
          if (response.ok) {
            const payload = await response.json() as { data?: { providers?: Array<{ provider: string; models?: string[]; completed?: number; failed?: number; updated_at?: string }>; analysis?: { processing_conversations?: number; pending_conversations?: number; failed_conversations?: number } } };
            system = { providers: (payload.data?.providers ?? []).map((p) => ({ provider: p.provider, models: p.models, completed: p.completed, failed: p.failed, updatedAt: p.updated_at })), analysis: payload.data?.analysis ?? null };
            systemAvailable = true;
          }
        } catch { /* unavailable stays explicit; stale data is never returned */ }
      }
    }
    return reply.send({ topics, system, systemAvailable, observedAt: new Date().toISOString() });
  });

  app.get('/api/v1/object-chat/conversations', async (request: FastifyRequest, reply: FastifyReply) => {
    const user = request.user!;
    const query = request.query as { limit?: string; kind?: string; q?: string; cursor?: string };
    const limit = boundedLimit(query.limit, 30, 100);
    const scope = await getZaloScope(user.id, user.orgId, user.role);
    const accountFilter = scope.isOrgAdmin ? {} : { zaloAccountId: { in: scope.displayableIds } };
    if (!scope.isOrgAdmin && scope.displayableIds.length === 0) return reply.send({ items: [] });
    const kind = query.kind === 'group' || query.kind === 'user' ? query.kind : undefined;
    const q = String(query.q ?? '').trim().slice(0, 120);
    if (query.cursor) {
      const cursorConversation = await prisma.conversation.findFirst({
        where: { id: query.cursor, orgId: user.orgId, deletedAt: null, ...accountFilter,
          ...(kind ? { threadType: kind } : {}),
          ...(q ? { OR: [{ groupName: { contains: q, mode: 'insensitive' } }, { contact: { fullName: { contains: q, mode: 'insensitive' } } }] } : {}) },
        select: { id: true },
      });
      if (!cursorConversation) return reply.code(400).send({ error: 'Cursor không hợp lệ' });
    }
    const items = await prisma.conversation.findMany({
      where: {
        orgId: user.orgId,
        deletedAt: null,
        ...accountFilter,
        ...(kind ? { threadType: kind } : {}),
        ...(q ? { OR: [{ groupName: { contains: q, mode: 'insensitive' } }, { contact: { fullName: { contains: q, mode: 'insensitive' } } }] } : {}),
      },
      select: {
        id: true, threadType: true, groupName: true, lastMessageAt: true,
        contact: { select: { fullName: true } },
        zaloAccount: { select: { displayName: true } },
        rockyAiObjects: { select: { id: true, naturalName: true, status: true, confidence: true, lastEvidenceAt: true } },
        rockyAiAnalysis: { select: { status: true, sourceObjectCount: true, sourceMessageCount: true, sourceLastMessageAt: true } },
      },
      orderBy: [{ lastMessageAt: 'desc' }, { id: 'asc' }], take: limit + 1,
      ...(query.cursor ? { cursor: { id: query.cursor }, skip: 1 } : {}),
    });
    const hasMore = items.length > limit;
    const page = items.slice(0, limit);
    return { items: page, nextCursor: hasMore ? page[page.length - 1].id : null };
  });

  app.get('/api/v1/object-chat/conversations/:conversationId/messages', async (request: FastifyRequest, reply: FastifyReply) => {
    const user = request.user!;
    const { conversationId } = request.params as { conversationId: string };
    const query = request.query as { limit?: string; cursor?: string; objectId?: string };
    const limit = boundedLimit(query.limit, 100, 100);
    const scope = await getZaloScope(user.id, user.orgId, user.role);
    const accountFilter = scope.isOrgAdmin ? {} : { zaloAccountId: { in: scope.displayableIds } };
    const conversation = await prisma.conversation.findFirst({ where: { id: conversationId, orgId: user.orgId, deletedAt: null, ...accountFilter }, select: { id: true } });
    if (!conversation) return reply.code(404).send({ error: 'Không tìm thấy hội thoại hoặc bạn không có quyền truy cập' });
    if (query.objectId) {
      const object = await prisma.rockyAiObject.findFirst({ where: { id: query.objectId, orgId: user.orgId, conversationId }, select: { id: true } });
      if (!object) return reply.code(404).send({ error: 'Không tìm thấy object trong hội thoại' });
    }
    const anchor = query.cursor ? decodeMessageCursor(query.cursor) : null;
    if (query.cursor && !anchor) return reply.code(400).send({ error: 'Cursor không hợp lệ' });
    const messages = await prisma.message.findMany({
      where: { conversationId, isDeleted: false, ...(query.objectId ? { rockyAiObjectEvidence: { some: { objectId: query.objectId } } } : {}),
        ...(anchor ? { OR: [{ sentAt: { lt: anchor.sentAt } }, { sentAt: anchor.sentAt, id: { lt: anchor.id } }] } : {}) },
      orderBy: [{ sentAt: 'desc' }, { id: 'desc' }], take: limit + 1,
      select: { id: true, senderType: true, senderName: true, content: true, contentType: true, attachments: true, sentAt: true },
    });
    const hasMore = messages.length > limit;
    const page = messages.slice(0, limit);
    const nextCursor = hasMore && page.length ? encodeMessageCursor(page[page.length - 1]) : null;
    return { items: page.reverse(), nextCursor };
  });

  app.get('/api/v1/object-chat/conversations/:conversationId/messages/:messageId/attachments', async (request: FastifyRequest, reply: FastifyReply) => {
    const user = request.user!;
    const { conversationId, messageId } = request.params as { conversationId: string; messageId: string };
    const scope = await getZaloScope(user.id, user.orgId, user.role);
    const accountFilter = scope.isOrgAdmin ? {} : { zaloAccountId: { in: scope.displayableIds } };
    const conversation = await prisma.conversation.findFirst({ where: { id: conversationId, orgId: user.orgId, deletedAt: null, ...accountFilter }, select: { rockyAiAnalysis: { select: { sourceConversationId: true } } } });
    const message = conversation && await prisma.message.findFirst({ where: { id: messageId, conversationId, isDeleted: false }, select: { zaloMsgId: true } });
    const sourceConversation = conversation?.rockyAiAnalysis?.sourceConversationId;
    const targetMessage = message?.zaloMsgId;
    if (!sourceConversation?.startsWith('pancake:rocky_pancake:') || !targetMessage?.startsWith('pancake:')) return reply.code(404).send({ error: 'Không tìm thấy tin nhắn' });
    const sourceMessage = `pancake:rocky_pancake:${targetMessage.slice('pancake:'.length)}`;
    try {
      const response = await fetch(`http://host.docker.internal:18082/api/chat/v1/conversations/${encodeURIComponent(sourceConversation)}/messages?limit=1&anchor_id=${encodeURIComponent(sourceMessage)}`, { signal: AbortSignal.timeout(15000) });
      if (!response.ok) return reply.code(502).send({ error: 'Không thể kiểm tra tệp nguồn' });
      const payload = await response.json() as { data?: Array<{ id: string; attachments?: Array<{ id: string; kind?: string; availability?: string; file_name?: string }> }> };
      const item = payload.data?.find((entry) => entry.id === sourceMessage);
      if (!item) return reply.code(404).send({ error: 'Không tìm thấy tin nhắn nguồn' });
      return { items: (item.attachments ?? []).map((attachment) => ({ id: attachment.id, kind: attachment.kind, availability: attachment.availability, fileName: attachment.file_name })) };
    } catch { return reply.code(502).send({ error: 'Không thể kiểm tra tệp nguồn' }); }
  });

  // Only the fixed Rocky service is contacted, after the local conversation,
  // message and requested attachment have all been verified in scope.
  app.get('/api/v1/object-chat/conversations/:conversationId/messages/:messageId/attachments/:attachmentId', async (request: FastifyRequest, reply: FastifyReply) => {
    const user = request.user!;
    const { conversationId, messageId, attachmentId } = request.params as { conversationId: string; messageId: string; attachmentId: string };
    const scope = await getZaloScope(user.id, user.orgId, user.role);
    const accountFilter = scope.isOrgAdmin ? {} : { zaloAccountId: { in: scope.displayableIds } };
    const conversation = await prisma.conversation.findFirst({ where: { id: conversationId, orgId: user.orgId, deletedAt: null, ...accountFilter }, select: { rockyAiAnalysis: { select: { sourceConversationId: true } } } });
    const message = conversation && await prisma.message.findFirst({ where: { id: messageId, conversationId, isDeleted: false }, select: { zaloMsgId: true } });
    const sourceConversation = conversation?.rockyAiAnalysis?.sourceConversationId;
    const targetMessage = message?.zaloMsgId;
    if (!sourceConversation?.startsWith('pancake:rocky_pancake:') || !targetMessage?.startsWith('pancake:')) return reply.code(404).send({ error: 'Không tìm thấy tệp đính kèm' });
    const sourceMessage = `pancake:rocky_pancake:${targetMessage.slice('pancake:'.length)}`;
    const base = 'http://host.docker.internal:18082/api/chat/v1';
    try {
      const lookup = await fetch(`${base}/conversations/${encodeURIComponent(sourceConversation)}/messages?limit=1&anchor_id=${encodeURIComponent(sourceMessage)}`, { signal: AbortSignal.timeout(15000) });
      if (!lookup.ok) return reply.code(502).send({ error: 'Không thể kiểm tra tệp nguồn' });
      const payload = await lookup.json() as { data?: Array<{ id: string; attachments?: Array<{ id: string; availability?: string }> }> };
      const sourceItem = payload.data?.find((item) => item.id === sourceMessage);
      if (!sourceItem?.attachments?.some((item) => item.id === attachmentId)) return reply.code(404).send({ error: 'Không tìm thấy tệp đính kèm' });
      const content = await fetch(`${base}/attachments/${encodeURIComponent(attachmentId)}/content`, { signal: AbortSignal.timeout(30000), redirect: 'error' });
      if (!content.ok || !content.body) return reply.code(content.status === 410 ? 410 : 502).send({ error: 'Tệp nguồn không khả dụng' });
      const maximum = 25 * 1024 * 1024;
      const reader = content.body.getReader(); const chunks: Uint8Array[] = []; let size = 0;
      for (;;) { const part = await reader.read(); if (part.done) break; size += part.value.byteLength; if (size > maximum) { await reader.cancel(); return reply.code(413).send({ error: 'Tệp vượt giới hạn kích thước' }); } chunks.push(part.value); }
      reply.header('Cache-Control', 'private, max-age=60').header('X-Content-Type-Options', 'nosniff').header('Content-Security-Policy', "default-src 'none'; sandbox");
      reply.type(content.headers.get('content-type') || 'application/octet-stream');
      const disposition = content.headers.get('content-disposition'); if (disposition) reply.header('Content-Disposition', disposition);
      return reply.send(Buffer.concat(chunks));
    } catch { return reply.code(502).send({ error: 'Không thể tải tệp nguồn' }); }
  });

  app.get('/api/v1/object-chat/conversations/:conversationId', async (request: FastifyRequest, reply: FastifyReply) => {
    const user = request.user!;
    const { conversationId } = request.params as { conversationId: string };
    const scope = await getZaloScope(user.id, user.orgId, user.role);
    const accountFilter = scope.isOrgAdmin ? {} : { zaloAccountId: { in: scope.displayableIds } };
    const conversation = await prisma.conversation.findFirst({
      where: { id: conversationId, orgId: user.orgId, deletedAt: null, ...accountFilter },
      select: {
        id: true, threadType: true, groupName: true, lastMessageAt: true,
        contact: { select: { fullName: true } },
        zaloAccount: { select: { displayName: true } },
        rockyAiAnalysis: { select: { status: true, sourceObjectCount: true, sourceMessageCount: true, sourceLastMessageAt: true } },
        rockyAiObjects: { orderBy: { id: 'asc' },
          select: { id: true, naturalName: true, objectType: true, summary: true, status: true, confidence: true, provider: true, model: true, firstEvidenceAt: true, lastEvidenceAt: true } },
      },
    });
    if (!conversation) return reply.code(404).send({ error: 'Không tìm thấy hội thoại hoặc bạn không có quyền truy cập' });
    const chronologicalObjects = [...conversation.rockyAiObjects].sort((left, right) => {
      const rightTime = right.lastEvidenceAt?.getTime() ?? 0;
      const leftTime = left.lastEvidenceAt?.getTime() ?? 0;
      return rightTime - leftTime || left.naturalName.localeCompare(right.naturalName, 'vi');
    });
    return { ...conversation, rockyAiObjects: chronologicalObjects };
  });
}
