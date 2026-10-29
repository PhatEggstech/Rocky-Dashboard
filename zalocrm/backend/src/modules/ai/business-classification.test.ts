import { describe, expect, it } from 'vitest';
import { validateBusinessExport, type BusinessExport } from './business-classification.js';

const valid: BusinessExport = { object_id: 'o', categories: ['ORDER'], labels: [{ category: 'ORDER', evidence_message_ids: ['m1'] }], version: 'business-v1', input_updated_at: 'v1', object_updated_at: 'v1', provider: 'local', model: 'model', evidence_examined: 1, classified_at: null, error: null, current: true };
describe('business classification import validation', () => {
  it('accepts current classifications grounded in the object evidence', () => {
    expect(validateBusinessExport(valid, new Set(['m1']))).toEqual({ eligible: true, reason: null });
    expect(validateBusinessExport({ ...valid, categories: [], labels: [] }, new Set())).toEqual({ eligible: true, reason: null });
  });
  it('rejects stale, ungrounded and mismatched labels', () => {
    expect(validateBusinessExport({ ...valid, object_updated_at: 'v2' }, new Set(['m1'])).reason).toBe('stale_or_unclassified');
    expect(validateBusinessExport({ ...valid, error: 'failure' }, new Set(['m1'])).reason).toBe('classification_failed');
    expect(validateBusinessExport(valid, new Set(['other'])).reason).toBe('evidence_outside_object');
    expect(validateBusinessExport({ ...valid, categories: ['PAYMENT'] }, new Set(['m1'])).reason).toBe('category_mismatch');
  });
});
