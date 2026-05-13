export interface TaskMetadata {
  id: string;
  task_type: string;
  difficulty?: string;
  capability_targets: string;
  evidence_layers: string;
  question?: string;
  prompt?: string;
  task_yaml: Record<string, unknown>;
  data_files: Array<{
    name: string;
    size_bytes: number;
    preview: string[];
  }>;
  gold_answer?: Record<string, unknown>;
}

export interface RunDetails {
  task_id: string;
  model: string;
  run_id: string;
  run_dir: string;
  command: string;
  returncode?: number;
  duration_seconds?: number;
  answer_text?: string;
  stdout_text?: string;
  stderr_text?: string;
  trace_text?: string;
  grade?: Record<string, unknown>;
  score?: number;
  timestamp: string;
  tags?: string[];
}

export interface PerformanceRun {
  run_id: string;
  task_id: string;
  model: string;
  timestamp: string;
  performance: {
    score?: number;
    duration_seconds?: number;
    token_usage?: {
      input_tokens?: number;
      output_tokens?: number;
      reasoning_tokens?: number;
    };
    cost_usd?: number;
  };
  tags: string[];
  artifacts: {
    trace_file: string;
    answer_file: string;
    grade_file: string;
  };
  metadata: {
    task_type: string;
    difficulty?: string;
    capability_targets: string[];
    evidence_layers: string[];
  };
}

export interface ModelSummary {
  tasks: number;
  mean_score?: number;
  parsed_rate?: number;
  error_rate?: number;
}

export interface DashboardData {
  tasks: TaskMetadata[];
  models: string[];
  model_summary: Record<string, ModelSummary>;
  latest_runs: Record<string, Record<string, RunDetails>>;
  task_tags?: Record<string, string[]>;
  runs?: RunDetails[];
}

export interface TaggedRun extends PerformanceRun {
  task: TaskMetadata;
}
