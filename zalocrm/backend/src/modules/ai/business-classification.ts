// SPDX-License-Identifier: AGPL-3.0-or-later
// Validate source evidence before an imported classification is eligible for a dashboard.
const categories = new Set(['NEED', 'CONSULTATION', 'ORDER', 'PAYMENT', 'COMPLAINT', 'RETURN', 'SUPPORT']);

export type BusinessExport = {
  object_id: string; categories: string[] | null; labels: unknown; version: string | null;
  input_updated_at: string | null; object_updated_at: string | null; provider: string | null;
  model: string | null; evidence_examined: number | null; classified_at: string | null;
  error: string | null; current: boolean;
};

export function validateBusinessExport(value: BusinessExport, allowedEvidence: ReadonlySet<string>): { eligible: boolean; reason: string | null } {
  if (value.error) return { eligible: false, reason: 'classification_failed' };
  if (!value.current || value.version !== 'business-v1' || !value.input_updated_at || value.input_updated_at !== value.object_updated_at) return { eligible: false, reason: 'stale_or_unclassified' };
  if (!Array.isArray(value.labels) || !Array.isArray(value.categories)) return { eligible: false, reason: 'invalid_contract' };
  const seen = new Set<string>();
  for (const label of value.labels) {
    if (!label || typeof label !== 'object') return { eligible: false, reason: 'invalid_contract' };
    const item = label as { category?: unknown; evidence_message_ids?: unknown };
    if (typeof item.category !== 'string' || !categories.has(item.category) || seen.has(item.category) || !Array.isArray(item.evidence_message_ids) || item.evidence_message_ids.length === 0 || item.evidence_message_ids.length > 4) return { eligible: false, reason: 'invalid_contract' };
    if (item.evidence_message_ids.some((id: unknown) => typeof id !== 'string' || !allowedEvidence.has(id))) return { eligible: false, reason: 'evidence_outside_object' };
    seen.add(item.category);
  }
  if (value.categories.length !== seen.size || value.categories.some((category) => !seen.has(category))) return { eligible: false, reason: 'category_mismatch' };
  return { eligible: true, reason: null };
}
