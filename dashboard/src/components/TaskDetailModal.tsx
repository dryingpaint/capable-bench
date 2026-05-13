'use client';

import { TaskMetadata, DashboardData } from '@/types/performance';
import { X, Tag } from 'lucide-react';
import { useState } from 'react';

interface TaskDetailModalProps {
  task: TaskMetadata;
  data: DashboardData;
  onClose: () => void;
}

export default function TaskDetailModal({ task, data, onClose }: TaskDetailModalProps) {
  const [activeTab, setActiveTab] = useState<'prompt' | 'metadata' | 'gold' | 'runs'>('prompt');

  const latestRuns = (data as any).latest_runs?.[task.id] || {};

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
    const runs = (data as any).runs || [];
    const run = runs.find((r: any) => r.task_id === task.id && r.model === model);
    return run?.tags || [];
  }

  function renderGoldAnswer() {
    if (!task.gold_answer || Object.keys(task.gold_answer).length === 0) {
      return <div className="text-stone-500">No gold answer available.</div>;
    }

    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <h4 className="text-green-800 font-bold text-sm mb-3 uppercase tracking-wide">
          Right Answer
        </h4>

        <div className="space-y-3 text-sm">
          {task.gold_answer.label_status && (
            <div className="text-stone-600">
              <strong>Label status:</strong> {task.gold_answer.label_status}
            </div>
          )}

          {task.gold_answer.gold_label !== undefined && (
            <div>
              <strong className="text-stone-700">Gold label:</strong>{' '}
              <span className="bg-green-200 text-green-800 px-2 py-1 rounded font-medium">
                {task.gold_answer.gold_label}
              </span>
            </div>
          )}

          {task.gold_answer.accepted_labels && Array.isArray(task.gold_answer.accepted_labels) && (
            <div>
              <strong className="text-stone-700">Accepted labels:</strong>
              <div className="flex flex-wrap gap-1 mt-1">
                {task.gold_answer.accepted_labels.map((label: any, index: number) => (
                  <span key={index} className="bg-stone-200 text-stone-700 px-2 py-1 rounded text-xs">
                    {label}
                  </span>
                ))}
              </div>
            </div>
          )}

          {task.gold_answer.rubric && (
            <div>
              <strong className="text-stone-700">Rubric:</strong>
              <pre className="bg-white border rounded p-2 mt-1 text-xs overflow-auto">
                {JSON.stringify(task.gold_answer.rubric, null, 2)}
              </pre>
            </div>
          )}

          <details className="mt-4">
            <summary className="cursor-pointer text-stone-600 text-xs font-medium">
              Raw gold YAML
            </summary>
            <pre className="bg-white border rounded p-2 mt-2 text-xs overflow-auto">
              {JSON.stringify(task.gold_answer, null, 2)}
            </pre>
          </details>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-6xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex justify-between items-start p-6 border-b border-stone-200">
          <div>
            <h2 className="text-xl font-bold text-stone-900 font-mono">{task.id}</h2>
            <div className="text-stone-600 text-sm mt-1">
              {[task.task_type, task.difficulty].filter(Boolean).join(' · ')}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-stone-100 rounded-lg transition-colors"
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
              onClick={() => setActiveTab(tab.id as any)}
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
                <pre className="bg-stone-50 border border-stone-200 rounded-lg p-4 text-sm whitespace-pre-wrap overflow-auto">
                  {task.prompt || 'No prompt available.'}
                </pre>
              </div>

              {task.data_files && task.data_files.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-3">Data Files</h3>
                  <div className="space-y-4">
                    {task.data_files.map((file, index) => (
                      <div key={index} className="border border-stone-200 rounded-lg p-4">
                        <h4 className="font-medium text-stone-900 mb-2">
                          {file.name} · {file.size_bytes} bytes
                        </h4>
                        <pre className="bg-stone-50 border rounded p-2 text-xs overflow-auto max-h-32">
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
              <pre className="bg-stone-50 border border-stone-200 rounded-lg p-4 text-sm overflow-auto">
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
                Captured command, answer artifact, combined agent trace, stdout, stderr, and grade for the latest run per model.
              </p>

              {data.models.map(model => {
                const run = latestRuns[model];
                const tags = getRunTags(model);

                if (!run) {
                  return (
                    <div key={model} className="border border-stone-200 rounded-lg p-4">
                      <h4 className="font-semibold text-stone-900 mb-2">
                        {model} · no run found
                      </h4>
                    </div>
                  );
                }

                return (
                  <details key={model} className="border border-stone-200 rounded-lg" open>
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
                              className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded bg-blue-100 text-blue-700"
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

                      <div className="space-y-4">
                        <div>
                          <h5 className="text-xs uppercase tracking-wider font-semibold text-stone-600 mb-2">
                            Command
                          </h5>
                          <pre className="bg-stone-50 border rounded p-2 text-xs overflow-auto">
                            {run.command}
                          </pre>
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                          <div>
                            <h5 className="text-xs uppercase tracking-wider font-semibold text-stone-600 mb-2">
                              Grade
                            </h5>
                            <pre className="bg-stone-50 border rounded p-2 text-xs overflow-auto max-h-60">
                              {JSON.stringify(run.grade, null, 2)}
                            </pre>
                          </div>

                          <div>
                            <h5 className="text-xs uppercase tracking-wider font-semibold text-stone-600 mb-2">
                              Answer Artifact
                            </h5>
                            <pre className="bg-stone-50 border rounded p-2 text-xs overflow-auto max-h-60">
                              {run.answer_text || 'No answer text'}
                            </pre>
                          </div>

                          <div>
                            <h5 className="text-xs uppercase tracking-wider font-semibold text-stone-600 mb-2">
                              Agent Trace
                            </h5>
                            <pre className="bg-stone-50 border rounded p-2 text-xs overflow-auto max-h-60">
                              {run.trace_text || 'No trace'}
                            </pre>
                          </div>

                          <div>
                            <h5 className="text-xs uppercase tracking-wider font-semibold text-stone-600 mb-2">
                              Stdout
                            </h5>
                            <pre className="bg-stone-50 border rounded p-2 text-xs overflow-auto max-h-60">
                              {run.stdout_text || 'No stdout'}
                            </pre>
                          </div>
                        </div>
                      </div>
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