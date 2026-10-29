// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * One-way, idempotent bridge from the existing Rocky Object Chat API.
 *
 * Conversation analysis state is imported even when it has no objects. Object
 * chronology is derived only from linked source-message timestamps, never from
 * the time that this bridge happened to run.
 */
import { prisma } from '../shared/database/prisma-client.js';

const base = (process.env.ROCKY_OBJECT_API_BASE || 'http://host.docker.internal:18082/api/chat/v1').replace(/\/$/, '');
const orgId = process.env.ROCKY_OBJECT_ORG_ID || '';
const prefix = 'pancake:rocky_pancake:';
if (!orgId) throw new Error('ROCKY_OBJECT_ORG_ID is required');

type SourceObject = { id: string; title: string; summary?: string; status?: string; review_status?: string };
type SourceMessage = { id: string };
type SourcePage<T> = { data: T[]; meta: { next_cursor: string | null } };
type SourceConversation = {
  id: string; analysis_status?: string; object_count?: number; message_count?: number;
  revision?: number; last_message_at?: string | null;
};

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${base}${path}`);
  if (!response.ok) throw new Error(`Rocky API ${response.status} at ${path}`);
  return response.json() as Promise<T>;
}
function targetExternalId(sourceConversationId: string): string | null {
  return sourceConversationId.startsWith(prefix) ? `pancake:${sourceConversationId.slice(prefix.length)}` : null;
}
function targetMessageId(sourceMessageId: string): string | null {
  return sourceMessageId.startsWith(prefix) ? `pancake:${sourceMessageId.slice(prefix.length)}` : null;
}
function sourceDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

async function allObjectMessages(conversationId: string, objectId: string): Promise<SourceMessage[]> {
  const messages: SourceMessage[] = [];
  let cursor: string | null = null;
  do {
    const page: SourcePage<SourceMessage> = await fetchJson<SourcePage<SourceMessage>>(
      `/conversations/${encodeURIComponent(conversationId)}/objects/${encodeURIComponent(objectId)}/messages?limit=250${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`,
    );
    messages.push(...page.data);
    cursor = page.meta.next_cursor;
  } while (cursor);
  return messages;
}

let cursor: string | null = null;
let importedAnalyses = 0;
let importedObjects = 0;
let importedEvidence = 0;
let skippedConversations = 0;
do {
  const page: SourcePage<SourceConversation> = await fetchJson<SourcePage<SourceConversation>>(
    `/conversations?limit=100${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`,
  );
  for (const sourceConversation of page.data) {
    const externalThreadId = targetExternalId(sourceConversation.id);
    if (!externalThreadId) { skippedConversations++; continue; }
    const target = await prisma.conversation.findFirst({ where: { orgId, externalThreadId }, select: { id: true } });
    if (!target) { skippedConversations++; continue; }

    await prisma.rockyAiConversationAnalysis.upsert({
      where: { conversationId: target.id },
      create: {
        orgId, conversationId: target.id, sourceConversationId: sourceConversation.id,
        status: sourceConversation.analysis_status ?? 'NOT_STARTED',
        sourceObjectCount: sourceConversation.object_count ?? 0,
        sourceMessageCount: sourceConversation.message_count ?? 0,
        sourceLastMessageAt: sourceDate(sourceConversation.last_message_at),
        metadata: { source_revision: sourceConversation.revision ?? null },
      },
      update: {
        status: sourceConversation.analysis_status ?? 'NOT_STARTED',
        sourceObjectCount: sourceConversation.object_count ?? 0,
        sourceMessageCount: sourceConversation.message_count ?? 0,
        sourceLastMessageAt: sourceDate(sourceConversation.last_message_at),
        metadata: { source_revision: sourceConversation.revision ?? null },
      },
    });
    importedAnalyses++;

    if (!sourceConversation.object_count) continue;
    const source = await fetchJson<{ data: SourceObject[] }>(`/conversations/${encodeURIComponent(sourceConversation.id)}/objects`);
    for (const object of source.data) {
      await prisma.rockyAiObject.upsert({
        where: { id: object.id },
        create: { id: object.id, orgId, conversationId: target.id, sourceObjectId: object.id, naturalName: object.title, summary: object.summary ?? null, status: object.review_status ?? object.status ?? 'proposed', provider: 'rocky-existing', model: 'preserved', analysisVersion: 'object-chat/v1' },
        update: { naturalName: object.title, summary: object.summary ?? null, status: object.review_status ?? object.status ?? 'proposed' },
      });
      importedObjects++;
      const sourceMessages = await allObjectMessages(sourceConversation.id, object.id);
      const externalMessageIds = sourceMessages.map((message) => targetMessageId(message.id)).filter((id): id is string => Boolean(id));
      if (externalMessageIds.length) {
        const targetMessages = await prisma.message.findMany({ where: { conversationId: target.id, zaloMsgId: { in: externalMessageIds } }, select: { id: true } });
        if (targetMessages.length) {
          const result = await prisma.rockyAiObjectEvidence.createMany({ data: targetMessages.map((message) => ({ objectId: object.id, messageId: message.id })), skipDuplicates: true });
          importedEvidence += result.count;
        }
      }
      const chronology = await prisma.message.aggregate({
        where: { conversationId: target.id, rockyAiObjectEvidence: { some: { objectId: object.id } } },
        _min: { sentAt: true }, _max: { sentAt: true },
      });
      await prisma.rockyAiObject.update({
        where: { id: object.id },
        data: { firstEvidenceAt: chronology._min.sentAt, lastEvidenceAt: chronology._max.sentAt },
      });
    }
  }
  cursor = page.meta.next_cursor;
} while (cursor);
console.log(JSON.stringify({ importedAnalyses, importedObjects, importedEvidence, skippedConversations }));
await prisma.$disconnect();
