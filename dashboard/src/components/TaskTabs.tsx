'use client';

import { useState } from 'react';
import Markdown from '@/components/Markdown';
import TaskDataFile from '@/components/TaskDataFile';
import { RunArtifactPanel } from '@/components/RunArtifactPanel';
import type { TaskMetadata, RunDetails } from '@/types/performance';

interface TaskTabsProps {
  task: TaskMetadata;
  models: string[];
  latestRuns: Record<string, RunDetails>;
  allRuns: Record<string, RunDetails[]>;
}

type TabId = 'problem' | 'runs';

export default function TaskTabs({ task, models, latestRuns, allRuns }: TaskTabsProps) {
  const [tab, setTab] = useState<TabId>('problem');
  const runCount = models.reduce((total, model) => total + (allRuns[model]?.length ?? 0), 0);

  return (
    <div>
      <div className="border-b border-stone-200 flex">
        <TabButton active={tab === 'problem'} onClick={() => setTab('problem')}>
          Problem
        </TabButton>
        <TabButton active={tab === 'runs'} onClick={() => setTab('runs')}>
          Runs <span className="text-stone-400 text-xs ml-1">({runCount})</span>
        </TabButton>
      </div>

      <div className="mt-6 space-y-8">
        {tab === 'problem' ? (
          <ProblemTab task={task} />
        ) : (
          <RunsTab task={task} models={models} latestRuns={latestRuns} allRuns={allRuns} />
        )}
      </div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
        active
          ? 'border-stone-900 text-stone-900'
          : 'border-transparent text-stone-600 hover:text-stone-900'
      }`}
    >
      {children}
    </button>
  );
}

function ProblemTab({ task }: { task: TaskMetadata }) {
  return (
    <>
      <section>
        <h2 className="text-lg font-semibold text-stone-900 mb-3">Prompt</h2>
        {task.prompt ? (
          <pre className="bg-white border border-stone-200 p-4 text-sm whitespace-pre-wrap overflow-auto">
            {task.prompt}
          </pre>
        ) : (
          <div className="text-stone-500 text-sm">No prompt available.</div>
        )}
      </section>

      {task.data_files && task.data_files.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-stone-900 mb-3">Data files</h2>
          <div className="space-y-2">
            {task.data_files.map((file) => (
              <TaskDataFile
                key={file.name}
                taskId={task.id}
                name={file.name}
                sizeBytes={file.size_bytes}
              />
            ))}
          </div>
        </section>
      )}

      <section>
        <h2 className="text-lg font-semibold text-stone-900 mb-3">Gold answer</h2>
        <GoldAnswer goldAnswer={task.gold_answer} />
      </section>

      <section>
        <h2 className="text-lg font-semibold text-stone-900 mb-3">Metadata</h2>
        <pre className="bg-stone-50 border border-stone-200 p-4 text-xs overflow-auto max-h-96">
          {JSON.stringify(task.task_yaml, null, 2)}
        </pre>
      </section>
    </>
  );
}

function RunsTab({
  task,
  models,
  latestRuns,
  allRuns,
}: {
  task: TaskMetadata;
  models: string[];
  latestRuns: Record<string, RunDetails>;
  allRuns: Record<string, RunDetails[]>;
}) {
  return (
    <section>
      <p className="text-sm text-stone-600 mb-3">
        Every recorded run for this task, grouped by model. Click any run to load and view its
        trace, stdout, and stderr — artifacts are fetched on demand.
      </p>
      <div className="space-y-6">
        {models.map((model) => {
          const runs = allRuns[model] ?? [];
          if (runs.length === 0) {
            return (
              <div key={model} className="border border-stone-200 bg-white p-4 text-sm text-stone-500">
                <span className="font-semibold text-stone-900">{model}</span> · no run found
              </div>
            );
          }
          const latestId = latestRuns[model]?.run_id;
          return (
            <div key={model}>
              <div className="text-xs uppercase tracking-wider font-semibold text-stone-500 mb-2">
                {model} · {runs.length} run{runs.length === 1 ? '' : 's'}
              </div>
              <div className="space-y-2">
                {runs.map((run) => (
                  <RunArtifactPanel
                    key={run.run_id}
                    taskId={task.id}
                    run={run}
                    isLatest={run.run_id === latestId}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function GoldAnswer({ goldAnswer }: { goldAnswer?: Record<string, unknown> }) {
  if (!goldAnswer || Object.keys(goldAnswer).length === 0) {
    return <div className="text-stone-500 text-sm">No gold answer available.</div>;
  }

  const labelStatus = typeof goldAnswer.label_status === 'string' ? goldAnswer.label_status : null;
  const goldLabel = printableValue(goldAnswer.gold_label);
  const acceptedLabels = Array.isArray(goldAnswer.accepted_labels)
    ? goldAnswer.accepted_labels
    : null;
  const rubric = goldAnswer.rubric;
  const goldReasoning =
    typeof goldAnswer.gold_reasoning === 'string' ? goldAnswer.gold_reasoning : null;

  return (
    <div className="bg-green-50 border border-green-200 p-4">
      <div className="space-y-3 text-sm">
        {labelStatus && (
          <div className="text-stone-600">
            <strong>Label status:</strong> {labelStatus}
          </div>
        )}

        {goldLabel !== null && (
          <div>
            <strong className="text-stone-700">Gold label:</strong>{' '}
            <span className="bg-green-200 text-green-800 px-2 py-1 font-medium">{goldLabel}</span>
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

        {goldReasoning && goldReasoning.trim().length > 0 && (
          <div className="mt-4 bg-white border border-green-200 p-4">
            <div className="text-green-800 font-bold text-xs uppercase tracking-wide mb-2">
              Gold reasoning
            </div>
            <div className="text-stone-800">
              <Markdown>{goldReasoning}</Markdown>
            </div>
          </div>
        )}

        <details className="mt-4">
          <summary className="cursor-pointer text-stone-600 text-xs font-medium">
            Raw gold YAML
          </summary>
          <pre className="bg-white border p-2 mt-2 text-xs overflow-auto">
            {JSON.stringify(goldAnswer, null, 2)}
          </pre>
        </details>
      </div>
    </div>
  );
}

function printableValue(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return JSON.stringify(value);
}
