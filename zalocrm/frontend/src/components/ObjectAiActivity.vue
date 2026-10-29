<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <section class="activity">
    <button class="activity-header" :aria-expanded="expanded" @click="expanded = !expanded">
      <span>{{ expanded ? 'Ẩn' : 'Xem' }} hoạt động AI</span>
      <small v-if="updatedAt">Cập nhật {{ format(updatedAt) }}</small>
    </button>
    <div v-if="expanded">
      <p v-if="error" class="note">Không cập nhật được trạng thái AI; vui lòng thử lại.</p>
      <template v-else-if="status">
        <p v-if="status.systemAvailable && status.system?.analysis" class="note">
          Hệ thống: {{ status.system.analysis.processing_conversations || 0 }} hội thoại đang xử lý · {{ status.system.analysis.pending_conversations || 0 }} đang chờ · {{ status.system.analysis.failed_conversations || 0 }} lỗi
        </p>
        <p v-else class="note">Trạng thái hệ thống chưa khả dụng hoặc không thuộc quyền xem của bạn.</p>
        <p v-for="provider in status.system?.providers || []" :key="provider.provider" class="note">
          {{ provider.provider === 'local' ? 'AI nội bộ' : provider.provider }}: {{ (provider.models || []).join(', ') || 'chưa rõ model' }} · {{ provider.completed || 0 }} job hoàn tất · lần cập nhật {{ provider.updatedAt ? format(provider.updatedAt) : 'chưa rõ' }}
        </p>
        <p class="note">Chủ đề gần đây trong bản ZaloCRM đã đồng bộ:</p>
        <button v-for="topic in status.topics" :key="topic.id" class="topic" @click="$emit('open', topic.conversationId)">
          {{ topic.naturalName }} <small>· {{ topic.conversation.groupName || topic.conversation.contact?.fullName || 'Hội thoại' }} · {{ format(topic.updatedAt) }}</small>
        </button>
        <p v-if="!status.topics.length" class="note">Chưa có chủ đề trong phạm vi được phép.</p>
        <p class="note">Cập nhật định kỳ 15 giây. Thời điểm chủ đề là lúc dữ liệu vào ZaloCRM; không phải luồng token hay suy luận trực tiếp của model.</p>
      </template>
    </div>
  </section>
</template>
<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { api } from '@/api';
type Provider = { provider: string; models?: string[]; completed?: number; updatedAt?: string };
type Status = { observedAt: string; systemAvailable: boolean; system: { providers: Provider[]; analysis: { processing_conversations?: number; pending_conversations?: number; failed_conversations?: number } | null } | null; topics: Array<{ id: string; naturalName: string; updatedAt: string; conversationId: string; conversation: { groupName: string | null; contact: { fullName: string | null } | null } }> };
defineEmits<{ open: [conversationId: string] }>();
const status=ref<Status | null>(null); const expanded=ref(false); const updatedAt=ref(''); const error=ref(false); let timer: ReturnType<typeof setInterval> | undefined; let busy=false; let disposed=false;
const format = (value: string) => new Intl.DateTimeFormat('vi-VN', { dateStyle: 'short', timeStyle: 'medium', timeZone: 'Asia/Ho_Chi_Minh' }).format(new Date(value));
async function refresh() { if (busy || document.hidden) return; busy=true; try { const { data } = await api.get('/object-chat/activity'); if (!disposed) { status.value=data; updatedAt.value=data.observedAt; error.value=false; } } catch { if (!disposed) error.value=true; } finally { busy=false; } }
function visible() { if (!document.hidden) void refresh(); }
onMounted(() => { void refresh(); timer=setInterval(refresh, 15000); document.addEventListener('visibilitychange', visible); });
onBeforeUnmount(() => { disposed=true; if (timer) clearInterval(timer); document.removeEventListener('visibilitychange', visible); });
</script>
<style scoped>
.activity{margin:12px 0;padding:10px;border:1px solid #dbe4ee;border-radius:8px;background:#f7fbff;min-width:0;line-height:1.5}
.activity-header,.topic{width:100%;height:auto;min-width:0;border:0;background:transparent;text-align:left;cursor:pointer;color:#175b87;white-space:normal;overflow-wrap:anywhere}
.activity-header{display:flex;flex-direction:column;align-items:flex-start;gap:3px;padding:2px 0 8px;font-weight:600;line-height:1.4}
.activity-header small{font-size:11px;font-weight:400;color:#667d92}
.topic{display:block;padding:7px 0;line-height:1.45;border-top:1px solid #e4edf4}
.topic small{display:block;color:#667d92;font-size:11px}
.note{color:#667d92;font-size:12px;line-height:1.5;margin:7px 0;overflow-wrap:anywhere}
</style>
