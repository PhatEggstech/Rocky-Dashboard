<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div ref="root" class="attachments">
    <button v-if="!loaded" :disabled="loading" @click="load">{{ loading ? 'Đang kiểm tra tệp...' : 'Xem ảnh / tệp đính kèm' }}</button>
    <span v-if="error" role="alert">{{ error }}</span>
    <span v-if="loaded && !items.length">Không có tệp khả dụng từ nguồn.</span>
    <div v-for="item in items" :key="item.id">
      <span v-if="item.kind === 'UNKNOWN'">Nội dung đính kèm chưa được nguồn hỗ trợ.</span>
      <button v-else-if="!item.url" :disabled="item.loading" @click="open(item)">{{ item.fileName || item.kind || 'Tệp đính kèm' }}</button>
      <img v-if="item.url && item.kind === 'IMAGE'" :src="item.url" :alt="item.fileName || 'Ảnh đính kèm'" />
      <a v-if="item.url" :href="item.url" :download="item.fileName || 'tep-dinh-kem'">Tải về</a>
      <span v-if="item.error">{{ item.error }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { api } from '@/api';
type Attachment = { id: string; kind?: string; fileName?: string; url?: string; loading?: boolean; error?: string };
const props = withDefaults(defineProps<{ conversationId: string; messageId: string; autoLoad?: boolean }>(), { autoLoad: false });
const items = ref<Attachment[]>([]); const loaded = ref(false); const loading = ref(false); const error = ref('');
const root = ref<HTMLElement | null>(null); let observer: IntersectionObserver | null = null; let disposed = false;
const base = () => `/object-chat/conversations/${encodeURIComponent(props.conversationId)}/messages/${encodeURIComponent(props.messageId)}/attachments`;
async function load() {
  loading.value=true; error.value='';
  try { const response = await api.get(base()); if (disposed) return; items.value=response.data.items; loaded.value=true; if (props.autoLoad) { for (const item of items.value) if (item.kind === 'IMAGE') await open(item); } }
  catch { error.value='Không thể kiểm tra tệp nguồn.'; }
  finally { loading.value=false; }
}
async function open(item: Attachment) {
  item.loading=true; item.error='';
  try { const response = await api.get(`${base()}/${encodeURIComponent(item.id)}`, { responseType: 'blob' }); if (!disposed) item.url=URL.createObjectURL(response.data); }
  catch { item.error='Không tải được tệp từ nguồn.'; }
  finally { item.loading=false; }
}
onMounted(() => { if (!props.autoLoad || !root.value) return; if (!('IntersectionObserver' in window)) { void load(); return; } observer = new IntersectionObserver((entries) => { if (entries.some((entry) => entry.isIntersecting)) { observer?.disconnect(); void load(); } }, { rootMargin: '100px' }); observer.observe(root.value); });
onBeforeUnmount(() => { disposed=true; observer?.disconnect(); for (const item of items.value) if (item.url) URL.revokeObjectURL(item.url); });
</script>
<style scoped>
.attachments{margin-top:8px;font-size:12px}.attachments button{cursor:pointer}.attachments img{display:block;max-width:240px;max-height:240px;object-fit:contain;margin:8px 0}.attachments span{color:#687d92}
</style>
