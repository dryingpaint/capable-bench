'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
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
  const [typeFilter, setTypeFilter] = useState('');
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: fetchDashboardData,
  });

  const toggleTypeFilter = (taskType: string) => {
    setTypeFilter(prev => (prev === taskType ? '' : taskType));
    if (typeof window !== 'undefined' && taskType) {
      const el = document.getElementById('tasks-table');
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

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
          <TasksTable data={data} typeFilter={typeFilter} setTypeFilter={setTypeFilter} />
        </div>
      </main>
    </div>
  );
}

export default function Dashboard() {
  return (
    <Providers>
      <DashboardContent />
    </Providers>
  );
}
