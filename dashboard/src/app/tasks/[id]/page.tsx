import Link from 'next/link';
import { notFound } from 'next/navigation';
import { ChevronLeft } from 'lucide-react';
import TaskTabs from '@/components/TaskTabs';
import { getTask, listTaskIds } from '@/lib/tasks';

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

  const { task, latestRuns, allRuns, models } = result;

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

      <main className="max-w-5xl mx-auto px-8 py-8">
        <TaskTabs task={task} models={models} latestRuns={latestRuns} allRuns={allRuns} />
      </main>
    </div>
  );
}
