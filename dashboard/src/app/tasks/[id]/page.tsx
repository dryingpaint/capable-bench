import Link from 'next/link';
import { notFound } from 'next/navigation';
import { ChevronLeft, ArrowRight, FileText } from 'lucide-react';
import TaskTabs from '@/components/TaskTabs';
import { getTask, listTaskIds } from '@/lib/tasks';
import { findingsLinkedToTask } from '@/lib/findings';

export const dynamicParams = false;

interface PageProps {
  params: Promise<{ id: string }>;
}

export async function generateStaticParams() {
  const ids = await listTaskIds();
  return ids.map((id) => ({ id }));
}

export async function generateMetadata({ params }: PageProps) {
  const { id } = await params;
  return { title: `${id} · Capable Bench` };
}

export default async function TaskPage({ params }: PageProps) {
  const { id } = await params;
  const result = await getTask(id);
  if (!result) notFound();

  const { task, latestRuns, models } = result;
  const linkedFindings = await findingsLinkedToTask(task.id);

  return (
    <div className="min-h-screen bg-stone-50">
      <header className="border-b border-stone-200 bg-white">
        <div className="max-w-5xl mx-auto px-8 py-6">
          <Link
            href="/"
            className="inline-flex items-center gap-1 text-sm text-stone-500 hover:text-stone-900 mb-3"
          >
            <ChevronLeft className="h-4 w-4" />
            All tasks
          </Link>
          <h1 className="text-xl font-mono font-bold text-stone-900">{task.id}</h1>
          <div className="text-sm text-stone-600 mt-1">{task.task_type}</div>
          <div className="flex flex-wrap gap-1 mt-3">
            {task.capability_targets
              ?.split(';')
              .map((item) => item.trim())
              .filter(Boolean)
              .map((capability) => (
                <span
                  key={capability}
                  className="inline-block px-2 py-0.5 text-xs bg-stone-100 text-stone-700"
                >
                  {capability}
                </span>
              ))}
            {task.evidence_layers
              ?.split(';')
              .map((item) => item.trim())
              .filter(Boolean)
              .map((evidence) => (
                <span
                  key={evidence}
                  className="inline-block px-2 py-0.5 text-xs bg-stone-100 text-stone-500 italic"
                >
                  {evidence}
                </span>
              ))}
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-8 py-8 space-y-6">
        {linkedFindings.length > 0 && (
          <section className="bg-stone-100 border border-stone-200 px-5 py-3">
            <div className="text-xs uppercase tracking-wider font-semibold text-stone-500 mb-2">
              Discussed in finding{linkedFindings.length === 1 ? '' : 's'}
            </div>
            <div className="space-y-2">
              {linkedFindings.map((finding) => (
                <Link
                  key={finding.id}
                  href={`/findings/${encodeURIComponent(finding.id)}`}
                  className="flex items-start gap-2 text-sm text-stone-800 bg-white border border-stone-300 px-3 py-2 hover:border-stone-500 hover:text-stone-900"
                >
                  <FileText className="h-4 w-4 mt-0.5 shrink-0 text-stone-500" />
                  <div className="min-w-0 flex-1">
                    <div className="font-medium truncate">{finding.title}</div>
                    <div className="text-xs text-stone-500 font-mono truncate">{finding.id}</div>
                  </div>
                  <ArrowRight className="h-3.5 w-3.5 mt-1 shrink-0 text-stone-400" />
                </Link>
              ))}
            </div>
          </section>
        )}

        <TaskTabs task={task} models={models} latestRuns={latestRuns} />
      </main>
    </div>
  );
}
