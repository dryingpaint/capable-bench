import { DashboardData } from '@/types/performance';

interface HeaderProps {
  data: DashboardData;
}

export default function Header({ data }: HeaderProps) {
  const taskTypes = [...new Set(data.tasks.map(t => t.task_type))].length;

  return (
    <header className="bg-gradient-to-b from-stone-100 to-stone-50 border-b border-stone-200">
      <div className="max-w-7xl mx-auto px-8 py-8">
        <div className="flex justify-between items-end gap-6 flex-wrap">
          <div>
            <div className="text-xs uppercase tracking-wider text-stone-600 font-semibold mb-2">
              Capable Bench
            </div>
            <h1 className="text-3xl font-bold text-stone-900 mb-1">
              Performance Dashboard
            </h1>
            <p className="text-stone-600">
              {data.tasks.length} tasks · {taskTypes} task types · {data.models.length} model{data.models.length === 1 ? '' : 's'} compared
            </p>
          </div>

          <div className="flex gap-3 flex-wrap">
            {data.calibration?.quality_gate_passed !== undefined && (
              <div className={`inline-flex items-center gap-2 px-3 py-2 rounded-full text-sm font-medium border ${
                data.calibration.quality_gate_passed
                  ? 'bg-green-50 text-green-700 border-green-200'
                  : 'bg-red-50 text-red-700 border-red-200'
              }`}>
                <div className={`w-2 h-2 rounded-full ${
                  data.calibration.quality_gate_passed ? 'bg-green-500' : 'bg-red-500'
                }`} />
                Calibration gate · {data.calibration.quality_gate_passed ? 'passed' : 'check'}
              </div>
            )}

            {data.calibration?.hard_fraction !== undefined && (
              <div className="inline-flex items-center gap-2 px-3 py-2 rounded-full text-sm font-medium bg-stone-100 text-stone-700 border border-stone-200">
                <div className="w-2 h-2 rounded-full bg-stone-600" />
                Hard fraction · {Math.round(data.calibration.hard_fraction * 100)}%
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}