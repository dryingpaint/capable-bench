/**
 * Human-readable labels for the internal task-type schema.
 *
 * Internal schema values (from data/answers/<id>.yaml `task_type`) map to the
 * names used in user-facing copy and in the memo. Keep this map in sync with
 * docs/openai-memo.md.
 */
const TASK_TYPE_LABELS: Record<string, string> = {
  next_experiment: 'Pairwise potency prediction',
  multitarget_activity: 'Multi-target activity prediction',
  hit_prediction: 'In-vivo hit prediction',
  candidate_prioritization: 'Candidate prioritization',
  program_lead_selection: 'Program lead selection',
};

export function taskTypeLabel(taskType: string | undefined | null): string {
  if (!taskType) return '';
  return TASK_TYPE_LABELS[taskType] ?? taskType;
}
