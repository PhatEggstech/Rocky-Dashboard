<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <main class="workspace">
    <aside class="list-pane">
      <h1>Hội thoại &amp; Object AI</h1>
      <p class="hint">Lịch sử gốc luôn đọc được, kể cả khi AI chưa có kết quả.</p>
      <ObjectAiActivity @open="openConversation" />
      <div class="filters">
        <input v-model="query" placeholder="Tìm khách hàng hoặc nhóm" @keyup.enter="loadConversations()" />
        <select v-model="kind" @change="loadConversations()"><option value="">Tất cả</option><option value="user">Cá nhân</option><option value="group">Nhóm</option></select>
      </div>
      <p v-if="listError" class="error">{{ listError }}</p>
      <button v-for="item in conversations" :key="item.id" class="conversation" :class="{ selected: item.id === selectedId }" @click="openConversation(item.id)">
        <strong>{{ title(item) }}</strong><span>{{ item.threadType === 'group' ? 'Nhóm' : 'Cá nhân' }} · {{ item.zaloAccount?.displayName || 'Nguồn import' }}</span>
        <small>{{ analysisLabel(item) }}</small>
      </button>
      <button v-if="listCursor" @click="loadConversations(true)">Tải thêm hội thoại</button>
    </aside>
    <section class="reader">
      <p v-if="!selected" class="empty">Chọn một hội thoại để đọc toàn bộ lịch sử.</p>
      <template v-else>
        <header><h2>{{ title(selected) }}</h2><p>{{ selected.zaloAccount?.displayName || 'Nguồn import' }}</p></header>
        <nav class="tabs"><button :class="{ active: activeObject === 'all' }" @click="selectObject('all')">Toàn bộ chat</button><button v-for="object in selected.rockyAiObjects" :key="object.id" :title="objectTime(object)" :class="{ active: activeObject === object.id }" @click="selectObject(object.id)">{{ object.naturalName }}</button></nav>
        <p v-if="selected.rockyAiObjects.length" class="hint">Object được sắp theo lần xuất hiện gần nhất trong hội thoại.</p>
        <p v-else class="hint">{{ analysisLabel(selected) }}</p>
        <div ref="timeline" class="timeline"><button v-if="messageCursor" :disabled="messagesLoading" @click="loadMessages(true)">{{ messagesLoading ? 'Đang tải...' : 'Tải tin cũ hơn' }}</button><article v-for="message in visibleMessages" :key="message.id" class="bubble" :class="message.senderType === 'self' ? 'self' : 'contact'"><div><strong>{{ message.senderName || (message.senderType === 'self' ? 'Nhân viên' : 'Người gửi') }}</strong><time>{{ formatTime(message.sentAt) }}</time></div><p v-if="message.content">{{ message.content }}</p><em v-else>{{ messageLabel(message) }}</em><ObjectChatAttachments v-if="hasMedia(message)" :conversation-id="selected.id" :message-id="message.id" auto-load /></article></div>
      </template>
      <p v-if="detailError" class="error">{{ detailError }}</p>
    </section>
  </main>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue';
import { api } from '@/api';
import ObjectChatAttachments from '@/components/ObjectChatAttachments.vue';
import ObjectAiActivity from '@/components/ObjectAiActivity.vue';
import { pancakeAttachmentDisplay } from '@/composables/pancake-attachments';
type Evidence = { messageId: string };
type AiObject = { id: string; naturalName: string; firstEvidenceAt?: string | null; lastEvidenceAt?: string | null; evidence?: Evidence[] };
type Message = { id: string; senderType: string; senderName: string | null; content: string | null; contentType: string; sentAt: string; attachments?: unknown };
type Analysis = { status: string; sourceObjectCount: number; sourceMessageCount: number; sourceLastMessageAt?: string | null };
type Conversation = { id: string; threadType: string; groupName: string | null; contact?: { fullName: string | null } | null; zaloAccount?: { displayName: string | null } | null; rockyAiObjects: AiObject[]; rockyAiAnalysis?: Analysis | null; messages?: Message[] };
const conversations = ref<Conversation[]>([]); const selected = ref<Conversation | null>(null); const selectedId = ref(''); const query = ref(''); const kind = ref(''); const activeObject = ref('all'); const listError = ref(''); const detailError = ref('');
const listCursor = ref<string | null>(null); const messageCursor = ref<string | null>(null); const visibleMessages = ref<Message[]>([]); let detailGeneration = 0; let listGeneration = 0;
const timeline = ref<HTMLElement | null>(null); const messagesLoading = ref(false);
const title = (item: Conversation) => item.groupName || item.contact?.fullName || 'Hội thoại chưa đặt tên';
const attachmentLabel = (type: string) => type === 'image' ? 'Hình ảnh' : type === 'file' ? 'Tệp đính kèm' : 'Tin nhắn không có nội dung chữ';
const hasMedia = (message: Message) => { const display = pancakeAttachmentDisplay(message.attachments); return display.hasRecordedType ? display.hasMedia : message.contentType !== 'text'; };
const messageLabel = (message: Message) => { const display = pancakeAttachmentDisplay(message.attachments); return display.label || (display.hasRecordedType && !display.hasKnownType ? 'Nội dung đính kèm chưa được hỗ trợ' : attachmentLabel(message.contentType)); };
const formatTime = (value: string) => new Intl.DateTimeFormat('vi-VN', { dateStyle: 'short', timeStyle: 'short', timeZone: 'Asia/Ho_Chi_Minh' }).format(new Date(value));
const objectTime = (object: AiObject) => object.lastEvidenceAt ? `Lần nhắc gần nhất: ${formatTime(object.lastEvidenceAt)}` : 'Chưa nối được bằng chứng theo thời gian';
const analysisLabel = (item: Conversation) => {
  if (item.rockyAiObjects.length) return `${item.rockyAiObjects.length} object AI`;
  const status = item.rockyAiAnalysis?.status;
  if (status === 'SUCCESS_EMPTY') return 'AI đã phân tích: không phát hiện object';
  if (status === 'FAILED') return 'AI phân tích lỗi — sẽ cần chạy lại';
  if (status === 'PROCESSING' || status === 'PENDING') return 'AI đang chờ/đang phân tích';
  if (status === 'SUCCESS') return 'AI đã phân tích: chưa có object được đồng bộ';
  return 'Chưa có kết quả AI';
};
async function loadConversations(more = false) { const generation = ++listGeneration; listError.value=''; try { const { data } = await api.get('/object-chat/conversations', { params: { limit: 30, q: query.value || undefined, kind: kind.value || undefined, cursor: more ? listCursor.value : undefined } }); if (generation !== listGeneration) return; conversations.value = more ? [...conversations.value, ...data.items] : data.items; listCursor.value = data.nextCursor; } catch { if (generation === listGeneration) listError.value='Không tải được danh sách hội thoại.'; } }
async function loadMessages(more = false) {
  if (more && messagesLoading.value) return;
  const generation = ++detailGeneration; const id = selectedId.value; const objectId = activeObject.value;
  const previousHeight = timeline.value?.scrollHeight ?? 0; const previousTop = timeline.value?.scrollTop ?? 0;
  messagesLoading.value=true; detailError.value='';
  try {
    const { data } = await api.get(`/object-chat/conversations/${encodeURIComponent(id)}/messages`, { params: { limit: 100, cursor: more ? messageCursor.value : undefined, objectId: objectId === 'all' ? undefined : objectId } });
    if (generation !== detailGeneration) return;
    visibleMessages.value = more ? [...data.items, ...visibleMessages.value] : data.items; messageCursor.value = data.nextCursor;
    await nextTick();
    if (generation !== detailGeneration || !timeline.value) return;
    timeline.value.scrollTop = more ? previousTop + timeline.value.scrollHeight - previousHeight : timeline.value.scrollHeight;
  } catch { if (generation === detailGeneration) detailError.value='Không tải được lịch sử hội thoại.'; }
  finally { if (generation === detailGeneration) messagesLoading.value=false; }
}
async function selectObject(id: string) { activeObject.value=id; visibleMessages.value=[]; messageCursor.value=null; await loadMessages(); }
async function openConversation(id: string) { const generation = ++detailGeneration; messagesLoading.value=false; selectedId.value=id; selected.value=null; visibleMessages.value=[]; activeObject.value='all'; messageCursor.value=null; detailError.value=''; try { const { data } = await api.get(`/object-chat/conversations/${encodeURIComponent(id)}`); if (generation !== detailGeneration) return; selected.value=data; await loadMessages(); } catch { if (generation === detailGeneration) detailError.value='Không tải được lịch sử hội thoại.'; } }
onMounted(loadConversations);
</script>

<style scoped>
.workspace{display:grid;grid-template-columns:340px minmax(0,1fr);height:calc(100vh - 48px);background:#f4f7fb}.list-pane{background:#fff;border-right:1px solid #dbe4ee;padding:18px;overflow:auto}.list-pane h1,h2{margin:0;color:#16324f}.hint{color:#687d92;font-size:13px}.filters{display:flex;gap:8px;margin:14px 0}.filters input,.filters select{min-width:0;padding:9px;border:1px solid #cedae7;border-radius:7px}.filters input{flex:1}.conversation{width:100%;display:flex;flex-direction:column;gap:4px;margin:6px 0;padding:12px;border:1px solid #e0e8f0;border-radius:9px;background:#fff;text-align:left;cursor:pointer}.conversation:hover,.selected{border-color:#1686be;background:#eff9ff}.conversation span,.conversation small{font-size:12px;color:#698096}.reader{min-width:0;display:flex;flex-direction:column;padding:20px}.reader header p{margin:4px 0;color:#687d92}.tabs{display:flex;gap:8px;overflow:auto;padding:12px 0;border-bottom:1px solid #dbe4ee}.tabs button{white-space:nowrap;border:1px solid #cedae7;background:#fff;border-radius:18px;padding:8px 12px;cursor:pointer}.tabs .active{background:#0b6f9f;color:#fff;border-color:#0b6f9f}.timeline{max-width:920px;overflow:auto;padding:16px 8px 72px}.bubble{max-width:76%;margin:10px 0;padding:11px 13px;border:1px solid #e0e8f0;border-radius:12px;background:#fff}.bubble.self{margin-left:auto;background:#e8f7ff;border-color:#bae3f5}.bubble div{display:flex;justify-content:space-between;gap:16px;font-size:12px;color:#60768b}.bubble p{white-space:pre-wrap;margin:7px 0 0;color:#21384d}.bubble em{display:block;margin-top:7px;color:#718398}.empty{margin:auto;color:#718398}.error{color:#b42318}@media(max-width:800px){.workspace{grid-template-columns:1fr}.list-pane{max-height:36vh;border-right:0;border-bottom:1px solid #dbe4ee}}
</style>
