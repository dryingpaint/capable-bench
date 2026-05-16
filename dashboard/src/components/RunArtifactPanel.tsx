'use client';

import { useEffect, useState } from 'react';
import { Tag } from 'lucide-react';
import type { RunDetails } from '@/types/performance';

interface RunArtifacts {
  answer_text: string;
  stdout_text: string;
  stderr_text: string;
  trace_text: string;
  truncated?: Record<string, boolean>;
}

function scoreClass(score: number | null | undefined): string {
  if (score === null || score === undefined) return 'text-stone-400';
  if (score < 0.4) return 'text-red-600';
  if (score < 0.6) return 'text-amber-600';
  return 'text-green-600';
}

function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return '—';
  return score.toFixed(3);
}

export function RunArtifactPanel({
  taskId,
  run,
  defaultOpen = true,
  isLatest = false,
}: {
  taskId: string;
  run: RunDetails;
  defaultOpen?: boolean;
  isLatest?: boolean;
}) {
  const tags = run.tags || [];
  const timestamp = run.timestamp ? new Date(run.timestamp).toISOString().replace('T', ' ').slice(0, 16) : '';
  return (
    <details className="border border-stone-200 bg-white" {...(defaultOpen ? { open: true } : {})}>
      <summary className="p-4 cursor-pointer text-stone-900 flex items-center gap-3 flex-wrap">
        <span className={`font-bold ${scoreClass(run.score)}`}>{formatScore(run.score)}</span>
        <span className="font-mono text-xs text-stone-700">{run.run_id}</span>
        {timestamp && <span className="text-xs text-stone-500">{timestamp}</span>}
        {isLatest && (
          <span className="inline-block text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200">
            latest
          </span>
        )}
        {tags.length > 0 && (
          <div className="flex gap-1">
            {tags.map((tag) => (
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
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4 text-sm">
          <div>
            <strong>Return code:</strong>
            <br />
            {run.returncode ?? '—'}
          </div>
          <div>
            <strong>Duration:</strong>
            <br />
            {run.duration_seconds ? `${run.duration_seconds.toFixed(2)}s` : '—'}
          </div>
          <div>
            <strong>Run dir:</strong>
            <br />
            <span className="font-mono text-xs break-all">{run.run_dir}</span>
          </div>
        </div>

        <RunArtifactDetails taskId={taskId} run={run} />
      </div>
    </details>
  );
}

function RunArtifactDetails({ taskId, run }: { taskId: string; run: RunDetails }) {
  const [artifacts, setArtifacts] = useState<RunArtifacts | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
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
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [taskId, run.run_id]);

  return (
    <div className="space-y-4">
      <div>
        <h5 className="text-xs uppercase tracking-wider font-semibold text-stone-600 mb-2">Command</h5>
        <pre className="bg-stone-50 border p-2 text-xs overflow-auto">{run.command}</pre>
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
