'use client';

import { TaskMetadata, DashboardData, RunDetails } from '@/types/performance';
import { X, Tag } from 'lucide-react';
import { useEffect, useState } from 'react';
import Markdown from './Markdown';

interface TaskDetailModalProps {
  task: TaskMetadata;
  data: DashboardData;
  onClose: () => void;
}

export default function TaskDetailModal({ task, data, onClose }: TaskDetailModalProps) {
  const [activeTab, setActiveTab] = useState<'prompt' | 'metadata' | 'gold' | 'runs'>('prompt');

  const latestRuns = data.latest_runs?.[task.id] || {};

  function getScoreClass(score: number | null | undefined): string {
    if (score === null || score === undefined) return 'text-stone-400';
    if (score < 0.4) return 'text-red-600';
    if (score < 0.6) return 'text-amber-600';
    return 'text-green-600';
  }

  function formatScore(score: number | null | undefined): string {
    if (score === null || score === undefined) return '—';
    return score.toFixed(3);
  }

  function getRunTags(model: string): string[] {
    return latestRuns[model]?.tags || [];
  }

  function renderGoldAnswer() {
    if (!task.gold_answer || Object.keys(task.gold_answer).length === 0) {
      return <div className="text-stone-500">No gold answer available.</div>;
    }
    const goldAnswer = task.gold_answer;
    const labelStatus = typeof goldAnswer.label_status === 'string' ? goldAnswer.label_status : null;
    const goldLabel = printableValue(goldAnswer.gold_label);
    const acceptedLabels = Array.isArray(goldAnswer.accepted_labels)
      ? goldAnswer.accepted_labels
      : null;
    const rubric = goldAnswer.rubric;

    return (
      <div className="bg-green-50 border border-green-200 p-4">
        <h4 className="text-green-800 font-bold text-sm mb-3 uppercase tracking-wide">
          Right Answer
        </h4>

        <div className="space-y-3 text-sm">
          {labelStatus && (
            <div className="text-stone-600">
              <strong>Label status:</strong> {labelStatus}
            </div>
          )}

          {goldLabel !== null && (
            <div>
              <strong className="text-stone-700">Gold label:</strong>{' '}
              <span className="bg-green-200 text-green-800 px-2 py-1 font-medium">
                {goldLabel}
              </span>
            </div>
          )}

          {acceptedLabels && (
            <div>
              <strong className="text-stone-700">Accepted labels:</strong>
              <div className="flex flex-wrap gap-1 mt-1">
                {acceptedLabels.map((label: unknown, index: number) => (
                  <span key={index} className="bg-stone-200 text-stone-700 px-2 py-1 text-xs">
                    {printableValue(label)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {rubric !== undefined && rubric !== null && (
            <div>
              <strong className="text-stone-700">Rubric:</strong>
              <pre className="bg-white border p-2 mt-1 text-xs overflow-auto">
                {JSON.stringify(rubric, null, 2)}
              </pre>
            </div>
          )}

          {typeof goldAnswer.gold_reasoning === 'string' && goldAnswer.gold_reasoning.trim().length > 0 && (
            <div className="mt-4 bg-white border border-green-200 p-4">
              <div className="text-green-800 font-bold text-xs uppercase tracking-wide mb-2">
                Gold reasoning
              </div>
              <div className="text-stone-800">
                <Markdown>{goldAnswer.gold_reasoning}</Markdown>
              </div>
            </div>
          )}

          <details className="mt-4">
            <summary className="cursor-pointer text-stone-600 text-xs font-medium">
              Raw gold YAML
            </summary>
            <pre className="bg-white border p-2 mt-2 text-xs overflow-auto">
              {JSON.stringify(task.gold_answer, null, 2)}
            </pre>
          </details>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white max-w-6xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex justify-between items-start p-6 border-b border-stone-200">
          <div>
            <h2 className="text-xl font-bold text-stone-900 font-mono">{task.id}</h2>
            <div className="text-stone-600 text-sm mt-1">
              {task.task_type}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-stone-100 transition-colors"
          >
            <X className="h-5 w-5 text-stone-600" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-stone-200 px-6">
          {[
            { id: 'prompt', label: 'Prompt' },
            { id: 'metadata', label: 'Metadata' },
            { id: 'gold', label: 'Gold Answer' },
            { id: 'runs', label: 'Runs' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as 'prompt' | 'metadata' | 'gold' | 'runs')}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-stone-900 text-stone-900'
                  : 'border-transparent text-stone-600 hover:text-stone-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {activeTab === 'prompt' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold mb-3">Prompt</h3>
                <pre className="bg-stone-50 border border-stone-200 p-4 text-sm whitespace-pre-wrap overflow-auto">
                  {task.prompt || 'No prompt available.'}
                </pre>
              </div>

              {task.data_files && task.data_files.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-3">Data Files</h3>
                  <div className="space-y-4">
                    {task.data_files.map((file, index) => (
                      <div key={index} className="border border-stone-200 p-4">
                        <h4 className="font-medium text-stone-900 mb-2">
                          {file.name} · {file.size_bytes} bytes
                        </h4>
                        <pre className="bg-stone-50 border p-2 text-xs overflow-auto max-h-32">
                          {file.preview.join('\n')}
                        </pre>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'metadata' && (
            <div>
              <h3 className="text-lg font-semibold mb-3">Task Metadata</h3>
              <pre className="bg-stone-50 border border-stone-200 p-4 text-sm overflow-auto">
                {JSON.stringify(task.task_yaml, null, 2)}
              </pre>
            </div>
          )}

          {activeTab === 'gold' && (
            <div>
              <h3 className="text-lg font-semibold mb-3">Gold Answer</h3>
              {renderGoldAnswer()}
            </div>
          )}

          {activeTab === 'runs' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Agent Traces & Artifacts</h3>
              <p className="text-sm text-stone-600">
                Latest run metadata loads with the dashboard. Large answer, trace, stdout, and stderr artifacts load when this panel opens.
              </p>

              {data.models.map(model => {
                const run = latestRuns[model];
                const tags = getRunTags(model);

                if (!run) {
                  return (
                    <div key={model} className="border border-stone-200 p-4">
                      <h4 className="font-semibold text-stone-900 mb-2">
                        {model} · no run found
                      </h4>
                    </div>
                  );
                }

                return (
                  <details key={model} className="border border-stone-200" open>
                    <summary className="p-4 cursor-pointer font-semibold text-stone-900 flex items-center gap-3">
                      <span>{model}</span>
                      <span className={`font-bold ${getScoreClass(run.score)}`}>
                        {formatScore(run.score)}
                      </span>
                      {tags.length > 0 && (
                        <div className="flex gap-1">
                          {tags.map(tag => (
                            <span
                              key={tag}
                              className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-blue-100 text-blue-700"
                            >
                              <Tag className="h-3 w-3" />
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </summary>
                    <div className="px-4 pb-4">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4 text-sm">
                        <div>
                          <strong>Run:</strong><br />
                          <span className="font-mono text-xs">{run.run_id}</span>
                        </div>
                        <div>
                          <strong>Return code:</strong><br />
                          {run.returncode ?? '—'}
                        </div>
                        <div>
                          <strong>Duration:</strong><br />
                          {run.duration_seconds ? `${run.duration_seconds.toFixed(2)}s` : '—'}
                        </div>
                        <div>
                          <strong>Run dir:</strong><br />
                          <span className="font-mono text-xs break-all">{run.run_dir}</span>
                        </div>
                      </div>

                      <RunArtifactDetails taskId={task.id} run={run} />
                    </div>
                  </details>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface RunArtifactDetailsProps {
  taskId: string;
  run: RunDetails;
}

interface RunArtifacts {
  answer_text: string;
  stdout_text: string;
  stderr_text: string;
  trace_text: string;
  truncated?: Record<string, boolean>;
}

function RunArtifactDetails({ taskId, run }: RunArtifactDetailsProps) {
  const [artifacts, setArtifacts] = useState<RunArtifacts | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadArtifacts() {
      try {
        setLoading(true);
        const url = `/run-artifacts/${encodeURIComponent(taskId)}/${encodeURIComponent(run.run_id)}.json`;
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error('Failed to load run artifacts');
        }
        const data = await response.json();
        if (!cancelled) {
          setArtifacts(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Unknown error');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadArtifacts();

    return () => {
      cancelled = true;
    };
  }, [taskId, run.run_id]);

  return (
    <div className="space-y-4">
      <div>
        <h5 className="text-xs uppercase tracking-wider font-semibold text-stone-600 mb-2">
          Command
        </h5>
        <pre className="bg-stone-50 border p-2 text-xs overflow-auto">
          {run.command}
        </pre>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ArtifactBlock title="Grade" text={JSON.stringify(run.grade, null, 2)} />

        {loading && (
          <div className="lg:col-span-2 text-sm text-stone-500 border border-stone-200 p-4">
            Loading artifacts...
          </div>
        )}

        {error && (
          <div className="lg:col-span-2 text-sm text-red-600 border border-red-200 bg-red-50 p-4">
            {error}
          </div>
        )}

        {artifacts && (
          <ArtifactBlock
            title="Answer Artifact"
            text={artifacts.answer_text || 'No answer text'}
            truncated={artifacts.truncated?.answer_text}
          />
        )}
      </div>

      {artifacts && (
        <ArtifactBlock
          title="Agent Trace"
          text={artifacts.trace_text || 'No trace'}
          truncated={artifacts.truncated?.trace_text}
          tall
        />
      )}

      {artifacts && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ArtifactBlock
            title="Stdout"
            text={artifacts.stdout_text || 'No stdout'}
            truncated={artifacts.truncated?.stdout_text}
          />
          <ArtifactBlock
            title="Stderr"
            text={artifacts.stderr_text || 'No stderr'}
            truncated={artifacts.truncated?.stderr_text}
          />
        </div>
      )}
    </div>
  );
}

function ArtifactBlock({
  title,
  text,
  truncated,
  tall,
}: {
  title: string;
  text: string;
  truncated?: boolean;
  tall?: boolean;
}) {
  return (
    <div>
      <h5 className="text-xs uppercase tracking-wider font-semibold text-stone-600 mb-2">
        {title}
        {truncated && <span className="normal-case tracking-normal text-stone-400"> · truncated</span>}
      </h5>
      <pre className={`bg-stone-50 border p-2 text-xs overflow-auto ${tall ? 'max-h-[36rem]' : 'max-h-60'}`}>
        {text}
      </pre>
    </div>
  );
}

function printableValue(value: unknown): string | null {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return JSON.stringify(value);
}
