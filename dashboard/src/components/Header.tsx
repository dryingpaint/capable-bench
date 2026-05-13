import { DashboardData } from '@/types/performance';

interface HeaderProps {
  data: DashboardData;
}

export default function Header({ data }: HeaderProps) {
  const taskTypes = [...new Set(data.tasks.map(t => t.task_type))].length;

  return (
    <header className="border-b border-stone-200">
      <div className="max-w-7xl mx-auto px-8 py-6">
        <h1 className="text-2xl font-semibold text-stone-900">Capable Bench</h1>
        <p className="text-sm text-stone-500 mt-1">
          {data.tasks.length} tasks · {taskTypes} task types · {data.models.length} model{data.models.length === 1 ? '' : 's'}
        </p>
      </div>
    </header>
  );
}
