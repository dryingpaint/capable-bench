import path from 'path';
import fs from 'fs/promises';
import type { DashboardData, TaskMetadata, RunDetails } from '@/types/performance';

const SAFE_ID = /^[A-Za-z0-9._-]+$/;

let cached: DashboardData | null = null;

async function loadDashboardData(): Promise<DashboardData> {
  if (cached) return cached;
  const dashboardJsonPath = path.resolve(process.cwd(), 'public', 'dashboard.json');
  const text = await fs.readFile(dashboardJsonPath, 'utf-8');
  cached = JSON.parse(text) as DashboardData;
  return cached;
}

export async function listTaskIds(): Promise<string[]> {
  const data = await loadDashboardData();
  return data.tasks.map((task) => task.id).filter((id) => SAFE_ID.test(id));
}

export async function getTask(id: string): Promise<{
  task: TaskMetadata;
  latestRuns: Record<string, RunDetails>;
  models: string[];
} | null> {
  if (!SAFE_ID.test(id)) return null;
  const data = await loadDashboardData();
  const task = data.tasks.find((t) => t.id === id);
  if (!task) return null;
  return {
    task,
    latestRuns: data.latest_runs?.[id] || {},
    models: data.models,
  };
}
