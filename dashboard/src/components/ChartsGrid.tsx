'use client';

import { DashboardData } from '@/types/performance';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

interface ChartsGridProps {
  data: DashboardData;
  onTaskTypeClick?: (taskType: string) => void;
  selectedTaskType?: string;
}

const COLORS = ['#1f4f53', '#c97064', '#d4a373', '#5a8a73', '#7b6c8a', '#c4a35a', '#456b8a'];

function colorFor(index: number) {
  return COLORS[index % COLORS.length];
}

export default function ChartsGrid({ data, onTaskTypeClick, selectedTaskType }: ChartsGridProps) {
  // Prepare leaderboard data. `aupFraction` is the share of tasks the model
  // refused under AUP — stacked onto the score bar so the visual reads as
  // "score + would-be-score if these tasks hadn't been refused".
  const leaderboardData = data.models
    .map((model, index) => {
      const tasks = data.model_summary[model]?.tasks || 0;
      const aupRefusals = data.model_summary[model]?.aup_refusal_count || 0;
      return {
        model,
        score: data.model_summary[model]?.mean_score || 0,
        tasks,
        aupRefusals,
        aupFraction: tasks > 0 ? aupRefusals / tasks : 0,
        color: colorFor(index),
      };
    })
    .sort((a, b) => b.score - a.score);

  // Prepare task type performance data
  const taskTypeData = [...new Set(data.tasks.map(t => t.task_type))].map(taskType => {
    const result: Record<string, string | number | null> = { taskType };

    data.models.forEach(model => {
      const tasksForType = data.tasks.filter(t => t.task_type === taskType);
      const scores: number[] = [];
      let aupCount = 0;
      tasksForType.forEach(task => {
        const runs = data.latest_runs?.[task.id];
        const run = runs?.[model];
        if (run?.score !== null && run?.score !== undefined) {
          scores.push(run.score);
        }
        if (run?.aup_refusal) aupCount += 1;
      });

      result[model] = scores.length > 0
        ? scores.reduce((a, b) => a + b, 0) / scores.length
        : null;
      result[`${model}__aup`] = aupCount;
      result[`${model}__aupFraction`] = tasksForType.length > 0 ? aupCount / tasksForType.length : 0;
    });

    return result;
  });

  const totalAupRefusals = leaderboardData.reduce((acc, m) => acc + m.aupRefusals, 0);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <svg width={0} height={0} style={{ position: 'absolute' }}>
        <defs>
          <pattern id="aup-stripes" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">
            <rect width="6" height="6" fill="#c97064" fillOpacity={0.18} />
            <line x1="0" y1="0" x2="0" y2="6" stroke="#c97064" strokeWidth="3" />
          </pattern>
        </defs>
      </svg>
      {/* Model Leaderboard */}
      <div className="lg:col-span-2 bg-white border border-stone-200 p-6">
        <div className="flex justify-between items-start mb-6">
          <div>
            <h3 className="text-lg font-semibold text-stone-900">Model Leaderboard</h3>
            <p className="text-sm text-stone-600">Mean score across all scored tasks (latest run per model)</p>
          </div>
          <div className="flex gap-4 text-xs text-stone-500 items-center">
            {data.models.map((model, index) => (
              <div key={model} className="flex items-center gap-2">
                <div
                  className="w-3 h-3"
                  style={{ backgroundColor: colorFor(index) }}
                />
                {model}
              </div>
            ))}
            {totalAupRefusals > 0 && (
              <div className="flex items-center gap-2 border-l border-stone-200 pl-3">
                <div className="w-3 h-3 border border-[#c97064]" style={{ background: 'repeating-linear-gradient(45deg, transparent 0 2px, #c97064 2px 4px)' }} />
                AUP refusal
              </div>
            )}
          </div>
        </div>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={leaderboardData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#e7e5e4" />
              <XAxis type="number" domain={[0, 1]} tickFormatter={(value) => value.toFixed(1)} />
              <YAxis
                type="category"
                dataKey="model"
                width={80}
                tick={{ fontSize: 12, fontWeight: 600 }}
              />
              <Tooltip
                formatter={(value, name, props) => {
                  if (name === 'aupFraction') {
                    const refused = props.payload?.aupRefusals ?? 0;
                    const tasks = props.payload?.tasks ?? 0;
                    return [`${refused} / ${tasks} tasks`, 'AUP-refused'];
                  }
                  return [
                    `${Number(value).toFixed(3)} · ${props.payload?.tasks ?? 0} tasks`,
                    'Mean score',
                  ];
                }}
              />
              <Bar dataKey="score" stackId="leaderboard" radius={[0, 0, 0, 0]}>
                {leaderboardData.map((entry, index) => (
                  <Cell key={`score-cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
              <Bar dataKey="aupFraction" stackId="leaderboard" fill="url(#aup-stripes)" radius={[0, 0, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Mean score by task type */}
      <div className="bg-white border border-stone-200 p-6">
        <div className="mb-6 flex items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-stone-900">Mean score by task type</h3>
            <p className="text-sm text-stone-600">
              {onTaskTypeClick ? 'Click a bar to filter the table below' : 'Per-model mean on each task family'}
            </p>
          </div>
          {selectedTaskType && onTaskTypeClick && (
            <button
              onClick={() => onTaskTypeClick(selectedTaskType)}
              className="text-xs text-stone-500 hover:text-stone-900 underline"
            >
              Clear filter
            </button>
          )}
        </div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={taskTypeData}
              onClick={(state) => {
                const label = state?.activeLabel;
                if (label !== undefined && onTaskTypeClick) {
                  onTaskTypeClick(String(label));
                }
              }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e7e5e4" />
              <XAxis
                dataKey="taskType"
                angle={-45}
                textAnchor="end"
                height={80}
                fontSize={11}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                tick={(props: any) => {
                  const value = String(props.payload?.value ?? '');
                  const x = Number(props.x ?? 0);
                  const y = Number(props.y ?? 0);
                  const isSelected = selectedTaskType === value;
                  return (
                    <text
                      x={x}
                      y={y}
                      dy={4}
                      textAnchor="end"
                      transform={`rotate(-45, ${x}, ${y})`}
                      fontSize={11}
                      fontWeight={isSelected ? 700 : 400}
                      fill={isSelected ? '#1c1917' : '#57534e'}
                    >
                      {value}
                    </text>
                  );
                }}
              />
              <YAxis domain={[0, 1]} tickFormatter={(value) => value.toFixed(1)} />
              <Tooltip
                cursor={onTaskTypeClick ? { fill: '#e7e5e4', opacity: 0.5 } : false}
                formatter={(value, name, props) => {
                  const key = String(name ?? '');
                  if (key.endsWith('__aupFraction')) {
                    const model = key.slice(0, -'__aupFraction'.length);
                    const aup = Number(props.payload?.[`${model}__aup`] ?? 0);
                    return [`${aup} task${aup === 1 ? '' : 's'}`, `${model} AUP-refused`];
                  }
                  return [
                    value === null || value === undefined ? '—' : Number(value).toFixed(3),
                    key,
                  ];
                }}
              />
              {data.models.flatMap((model, index) => [
                <Bar
                  key={`${model}-score`}
                  dataKey={model}
                  stackId={model}
                  fill={colorFor(index)}
                  radius={[0, 0, 0, 0]}
                  style={onTaskTypeClick ? { cursor: 'pointer' } : undefined}
                />,
                <Bar
                  key={`${model}-aup`}
                  dataKey={`${model}__aupFraction`}
                  stackId={model}
                  fill="url(#aup-stripes)"
                  radius={[0, 0, 0, 0]}
                />,
              ])}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
