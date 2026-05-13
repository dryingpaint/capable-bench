'use client';

import { useState, useMemo } from 'react';
import { DashboardData, TaskMetadata } from '@/types/performance';
import { Search, Tag } from 'lucide-react';
import TaskDetailModal from './TaskDetailModal';

interface TasksTableProps {
  data: DashboardData;
}

export default function TasksTable({ data }: TasksTableProps) {
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [difficultyFilter, setDifficultyFilter] = useState('');
  const [modelFilter, setModelFilter] = useState('');
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  const taskTypes = useMemo(() =>
    [...new Set(data.tasks.map(t => t.task_type))].sort(),
    [data.tasks]
  );

  const difficulties = useMemo(() =>
    [...new Set(data.tasks.map(t => t.difficulty).filter(Boolean))].sort(),
    [data.tasks]
  );

  const visibleModels = modelFilter ? [modelFilter] : data.models;

  const filteredTasks = useMemo(() => {
    return data.tasks.filter(task => {
      // Type filter
      if (typeFilter && task.task_type !== typeFilter) return false;

      // Difficulty filter
      if (difficultyFilter && task.difficulty !== difficultyFilter) return false;

      // Search filter
      if (search) {
        const searchLower = search.toLowerCase();
        const searchText = [
          task.id,
          task.task_type,
          task.question || '',
          task.capability_targets,
          task.evidence_layers
        ].join(' ').toLowerCase();

        if (!searchText.includes(searchLower)) return false;
      }

      return true;
    });
  }, [data.tasks, search, typeFilter, difficultyFilter]);

  function formatScore(score: number | null | undefined): string {
    if (score === null || score === undefined) return '—';
    return score.toFixed(3);
  }

  function getScoreClass(score: number | null | undefined): string {
    if (score === null || score === undefined) return 'text-stone-400';
    if (score < 0.4) return 'text-red-600';
    if (score < 0.6) return 'text-amber-600';
    return 'text-green-600';
  }

  function renderPills(value: string | undefined): React.ReactNode {
    if (!value) return null;
    return value.split(';').map(item => item.trim()).filter(Boolean).map((item, index) => (
      <span key={index} className="inline-block px-2 py-1 text-xs rounded-md bg-stone-100 text-stone-700 mr-1 mb-1">
        {item}
      </span>
    ));
  }

  function getRunTags(taskId: string, model: string): string[] {
    return data.latest_runs?.[taskId]?.[model]?.tags || [];
  }

  function getTaskTags(task: TaskMetadata): string[] {
    return data.task_tags?.[task.id] || [task.task_type, task.difficulty].filter((tag): tag is string => Boolean(tag));
  }

  function getTagColor(tag: string): string {
    if (tag === 'easy') return 'bg-green-100 text-green-800';
    if (tag === 'medium') return 'bg-amber-100 text-amber-800';
    if (tag === 'hard') return 'bg-red-100 text-red-800';
    return 'bg-blue-100 text-blue-800'; // Default for task types
  }

  const selectedTask = selectedTaskId ? data.tasks.find(t => t.id === selectedTaskId) : null;

  return (
    <>
      <div className="bg-white border border-stone-200 rounded-xl shadow-sm overflow-hidden">
        <div className="p-6 border-b border-stone-200 bg-stone-50">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-stone-900">Tasks</h3>
            <div className="text-sm text-stone-600">
              {filteredTasks.length} of {data.tasks.length} task{data.tasks.length === 1 ? '' : 's'} shown
            </div>
          </div>

          {/* Filters */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-3 h-4 w-4 text-stone-400" />
              <input
                type="text"
                placeholder="Search tasks, questions, capabilities..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-stone-500 focus:border-transparent"
              />
            </div>

            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="px-4 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-stone-500"
            >
              <option value="">All types</option>
              {taskTypes.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>

            <select
              value={difficultyFilter}
              onChange={(e) => setDifficultyFilter(e.target.value)}
              className="px-4 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-stone-500"
            >
              <option value="">All difficulties</option>
              {difficulties.map(diff => (
                <option key={diff} value={diff}>{diff}</option>
              ))}
            </select>

            <select
              value={modelFilter}
              onChange={(e) => setModelFilter(e.target.value)}
              className="px-4 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-stone-500"
            >
              <option value="">All model columns</option>
              {data.models.map(model => (
                <option key={model} value={model}>{model}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-stone-50 border-b border-stone-200">
                <th className="text-left py-3 px-4 font-semibold text-stone-900 text-xs uppercase tracking-wider min-w-[350px]">
                  Question
                </th>
                <th className="text-left py-3 px-4 font-semibold text-stone-900 text-xs uppercase tracking-wider">
                  Capabilities
                </th>
                <th className="text-left py-3 px-4 font-semibold text-stone-900 text-xs uppercase tracking-wider">
                  Evidence
                </th>
                {visibleModels.map(model => (
                  <th key={model} className="text-left py-3 px-4 font-semibold text-stone-900 text-xs uppercase tracking-wider">
                    {model}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredTasks.length === 0 ? (
                <tr>
                  <td colSpan={3 + visibleModels.length} className="py-12 text-center text-stone-500">
                    No tasks match the current filters.
                  </td>
                </tr>
              ) : (
                filteredTasks.map(task => {
                  const latestRuns = data.latest_runs?.[task.id] || {};
                  const taskTags = getTaskTags(task);

                  return (
                    <tr
                      key={task.id}
                      className="border-b border-stone-100 hover:bg-stone-50 cursor-pointer"
                      onClick={() => setSelectedTaskId(task.id)}
                    >
                      <td className="py-4 px-4">
                        {task.question ? (
                          <div className="text-stone-900 text-sm font-medium mb-2 max-w-md">
                            {task.question.length > 180 ? task.question.substring(0, 180) + '...' : task.question}
                          </div>
                        ) : (
                          <div className="text-stone-900 text-sm font-medium mb-2">
                            {task.id}
                          </div>
                        )}
                        <div className="flex flex-wrap gap-1 mb-1">
                          {taskTags.map(tag => (
                            <span
                              key={tag}
                              className={`inline-block px-2 py-1 text-xs rounded-md font-medium ${getTagColor(tag)}`}
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                        <div className="font-mono text-xs text-stone-500">
                          {task.id}
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        {renderPills(task.capability_targets)}
                      </td>
                      <td className="py-4 px-4">
                        {renderPills(task.evidence_layers)}
                      </td>
                      {visibleModels.map(model => {
                        const run = latestRuns[model];
                        const tags = getRunTags(task.id, model);

                        if (!run) {
                          return (
                            <td key={model} className="py-4 px-4">
                              <div className="text-stone-400">—</div>
                            </td>
                          );
                        }

                        const parsed = run.grade?.parsed_answer !== false;
                        const rcOk = run.returncode === 0 || run.returncode == null;

                        return (
                          <td key={model} className="py-4 px-4">
                            <div className={`font-bold text-sm ${getScoreClass(run.score)}`}>
                              {formatScore(run.score)}
                            </div>
                            {run.score !== null && run.score !== undefined && (
                              <div className="w-16 h-1 bg-stone-200 rounded-full mt-1 overflow-hidden">
                                <div
                                  className="h-full bg-stone-600 rounded-full"
                                  style={{ width: `${Math.max(2, Math.min(100, run.score * 100))}%` }}
                                />
                              </div>
                            )}
                            <div className="text-xs text-stone-500 mt-1 font-mono">
                              {run.run_id}
                              {!parsed && ' · unparsed'}
                              {!rcOk && ` · rc=${run.returncode}`}
                            </div>
                            {tags.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-1">
                                {tags.map(tag => (
                                  <span
                                    key={tag}
                                    className="inline-flex items-center gap-1 px-1.5 py-0.5 text-xs rounded bg-blue-100 text-blue-700"
                                  >
                                    <Tag className="h-2.5 w-2.5" />
                                    {tag}
                                  </span>
                                ))}
                              </div>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {selectedTask && (
        <TaskDetailModal
          task={selectedTask}
          data={data}
          onClose={() => setSelectedTaskId(null)}
        />
      )}
    </>
  );
}
