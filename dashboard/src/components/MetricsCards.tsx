import { DashboardData } from '@/types/performance';

interface MetricsCardsProps {
  data: DashboardData;
}

type MetricCard = {
  label: string;
  value: string | number;
  delta: string;
  accent?: boolean;
};

export default function MetricsCards({ data }: MetricsCardsProps) {
  const taskTypes = [...new Set(data.tasks.map(t => t.task_type))].length;
  const hardTasks = data.tasks.filter(t => t.difficulty?.toLowerCase() === 'hard').length;

  // Calculate top performing model
  const ranked = data.models
    .map(m => ({
      model: m,
      score: data.model_summary[m]?.mean_score
    }))
    .filter(({ score }) => score !== null && score !== undefined)
    .sort((a, b) => (b.score || 0) - (a.score || 0));

  const cards: MetricCard[] = [
    {
      label: 'Tasks',
      value: data.tasks.length.toString(),
      delta: `${taskTypes} task types`,
    },
    {
      label: 'Hard tasks',
      value: hardTasks.toString(),
      delta: `${Math.round(100 * hardTasks / Math.max(data.tasks.length, 1))}% of suite`,
    },
    {
      label: 'Models scored',
      value: data.models.length || '—',
      delta: data.models.join(' · ') || 'no runs yet',
    },
  ];

  if (ranked.length > 0) {
    const topModel = ranked[0];
    cards.push({
      label: 'Top mean score',
      value: topModel.score?.toFixed(3) || '—',
      delta: topModel.model,
      accent: true,
    });

    if (ranked.length > 1) {
      const secondModel = ranked[1];
      const delta = (topModel.score || 0) - (secondModel.score || 0);
      cards.push({
        label: 'Runner-up',
        value: secondModel.score?.toFixed(3) || '—',
        delta: `${secondModel.model} · Δ ${delta.toFixed(3)}`,
      });
    }
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className={`
            bg-white border border-stone-200 rounded-xl p-4 shadow-sm
            ${card.accent ? 'bg-gradient-to-br from-stone-50 to-white' : ''}
          `}
        >
          <div className="text-xs uppercase tracking-wider text-stone-500 font-semibold mb-2">
            {card.label}
          </div>
          <div className="text-2xl font-bold text-stone-900 mb-1">
            {card.value}
          </div>
          <div className="text-sm text-stone-600">
            {card.delta}
          </div>
        </div>
      ))}
    </div>
  );
}
