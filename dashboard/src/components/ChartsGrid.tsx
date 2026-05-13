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
}

const COLORS = ['#1f4f53', '#c97064', '#d4a373', '#5a8a73', '#7b6c8a', '#c4a35a', '#456b8a'];

function colorFor(index: number) {
  return COLORS[index % COLORS.length];
}

export default function ChartsGrid({ data }: ChartsGridProps) {
  // Prepare leaderboard data
  const leaderboardData = data.models
    .map((model, index) => ({
      model,
      score: data.model_summary[model]?.mean_score || 0,
      tasks: data.model_summary[model]?.tasks || 0,
      color: colorFor(index),
    }))
    .sort((a, b) => b.score - a.score);

  // Prepare task type performance data
  const taskTypeData = [...new Set(data.tasks.map(t => t.task_type))].map(taskType => {
    const result: Record<string, string | number | null> = { taskType };

    data.models.forEach(model => {
      const scores: number[] = [];
      data.tasks
        .filter(t => t.task_type === taskType)
        .forEach(task => {
          const runs = data.latest_runs?.[task.id];
          const run = runs?.[model];
          if (run?.score !== null && run?.score !== undefined) {
            scores.push(run.score);
          }
        });

      result[model] = scores.length > 0
        ? scores.reduce((a, b) => a + b, 0) / scores.length
        : null;
    });

    return result;
  });

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Model Leaderboard */}
      <div className="lg:col-span-2 bg-white border border-stone-200 rounded-xl p-6 shadow-sm">
        <div className="flex justify-between items-start mb-6">
          <div>
            <h3 className="text-lg font-semibold text-stone-900">Model Leaderboard</h3>
            <p className="text-sm text-stone-600">Mean score across all scored tasks (latest run per model)</p>
          </div>
          <div className="flex gap-4 text-xs text-stone-500">
            {data.models.map((model, index) => (
              <div key={model} className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded"
                  style={{ backgroundColor: colorFor(index) }}
                />
                {model}
              </div>
            ))}
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
                formatter={(value, _name, props) => [
                  `${Number(value).toFixed(3)} · ${props.payload?.tasks ?? 0} tasks`,
                  'Mean score'
                ]}
              />
              <Bar dataKey="score" radius={[0, 6, 6, 0]}>
                {leaderboardData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Mean score by task type */}
      <div className="bg-white border border-stone-200 rounded-xl p-6 shadow-sm">
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-stone-900">Mean score by task type</h3>
          <p className="text-sm text-stone-600">Per-model mean on each task family</p>
        </div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={taskTypeData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e7e5e4" />
              <XAxis
                dataKey="taskType"
                angle={-45}
                textAnchor="end"
                height={80}
                fontSize={11}
              />
              <YAxis domain={[0, 1]} tickFormatter={(value) => value.toFixed(1)} />
              <Tooltip
                formatter={(value, name) => [
                  value === null || value === undefined ? '—' : Number(value).toFixed(3),
                  String(name ?? '')
                ]}
              />
              {data.models.map((model, index) => (
                <Bar
                  key={model}
                  dataKey={model}
                  fill={colorFor(index)}
                  radius={[2, 2, 0, 0]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
