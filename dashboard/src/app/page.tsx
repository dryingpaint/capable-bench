'use client';

import { Suspense, useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { DashboardData } from '@/types/performance';
import Header from '@/components/Header';
import ChartsGrid from '@/components/ChartsGrid';
import TasksTable from '@/components/TasksTable';
import { Providers } from '@/components/Providers';
import { FileText } from 'lucide-react';

async function fetchDashboardData(): Promise<DashboardData> {
  const response = await fetch('/dashboard.json');
  if (!response.ok) {
    throw new Error('Failed to fetch dashboard data');
  }
  return response.json();
}

function DashboardContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const typeFilter = searchParams.get('type') ?? '';
  const modelFilter = searchParams.get('model') ?? '';
  const search = searchParams.get('q') ?? '';

  const updateParam = useCallback(
    (key: string, value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
      const query = params.toString();
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  const setTypeFilter = useCallback((value: string) => updateParam('type', value), [updateParam]);
  const setModelFilter = useCallback((value: string) => updateParam('model', value), [updateParam]);
  const setSearch = useCallback((value: string) => updateParam('q', value), [updateParam]);

  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: fetchDashboardData,
  });

  const toggleTypeFilter = useCallback(
    (taskType: string) => {
      const next = typeFilter === taskType ? '' : taskType;
      setTypeFilter(next);
      if (typeof window !== 'undefined' && next) {
        const el = document.getElementById('tasks-table');
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    },
    [typeFilter, setTypeFilter],
  );

  const filterState = useMemo(
    () => ({ search, typeFilter, modelFilter, setSearch, setTypeFilter, setModelFilter }),
    [search, typeFilter, modelFilter, setSearch, setTypeFilter, setModelFilter],
  );

  if (isLoading) {
    return (
      <div className="min-h-screen bg-stone-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-stone-900 mx-auto mb-4"></div>
          <p className="text-stone-600">Loading performance data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-stone-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">Error loading dashboard data</p>
          <p className="text-stone-600 text-sm">{error.message}</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <div className="min-h-screen bg-stone-50">
      <Header data={data} />

      <main className="max-w-7xl mx-auto px-8 py-6 space-y-6">
        <div className="flex justify-end">
          <Link
            href="/findings"
            className="inline-flex items-center gap-1.5 text-sm text-stone-600 hover:text-stone-900 transition-colors"
          >
            <FileText className="h-3.5 w-3.5" />
            Case studies and reports
          </Link>
        </div>

        <ChartsGrid
          data={data}
          onTaskTypeClick={toggleTypeFilter}
          selectedTaskType={typeFilter}
        />
        <div id="tasks-table">
          <TasksTable data={data} {...filterState} />
        </div>
      </main>
    </div>
  );
}

export default function Dashboard() {
  return (
    <Providers>
      <Suspense fallback={null}>
        <DashboardContent />
      </Suspense>
    </Providers>
  );
}
