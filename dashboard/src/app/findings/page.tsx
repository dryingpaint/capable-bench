import Link from 'next/link';
import { ArrowLeft, Calendar, FileText, ChevronRight } from 'lucide-react';
import { listFindings } from '@/lib/findings';

export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'Research Findings · Capable Bench',
};

export default async function FindingsPage() {
  const findings = await listFindings();

  return (
    <div className="min-h-screen bg-stone-50">
      <header className="bg-gradient-to-b from-stone-100 to-stone-50 border-b border-stone-200">
        <div className="max-w-6xl mx-auto px-8 py-8">
          <Link
            href="/"
            className="inline-flex items-center gap-1 text-sm text-stone-600 hover:text-stone-900 mb-4"
          >
            <ArrowLeft className="h-4 w-4" />
            Dashboard
          </Link>
          <div className="text-xs uppercase tracking-wider text-stone-600 font-semibold mb-2">
            Capable Bench
          </div>
          <h1 className="text-3xl font-bold text-stone-900 mb-1">Research Findings</h1>
          <p className="text-stone-600">
            {findings.length} finding{findings.length === 1 ? '' : 's'} — diagnostic results that
            expose specific reasoning failures, blind spots, or calibration issues.
          </p>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-8 py-8">
        {findings.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="space-y-3">
            {findings.map((finding) => (
              <Link
                key={finding.id}
                href={`/findings/${finding.id}`}
                className="block border border-stone-200 rounded-lg bg-white hover:border-stone-300 hover:shadow-sm transition-all"
              >
                <div className="px-5 py-4 flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h2 className="font-semibold text-stone-900 mb-1 truncate">
                      {finding.title}
                    </h2>
                    <div className="text-xs text-stone-500 font-mono mb-2 truncate">
                      {finding.id}
                    </div>
                    {finding.preview && (
                      <p className="text-sm text-stone-600 whitespace-pre-line line-clamp-2 mb-2">
                        {finding.preview}
                      </p>
                    )}
                    <div className="flex items-center gap-4 text-xs text-stone-500">
                      <span className="inline-flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        {new Date(finding.lastModified).toLocaleDateString()}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <FileText className="h-3 w-3" />
                        {finding.artifactCount} artifact{finding.artifactCount === 1 ? '' : 's'}
                      </span>
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-stone-400 mt-1 shrink-0" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="text-center py-16">
      <FileText className="h-10 w-10 mx-auto mb-3 text-stone-400" />
      <p className="text-stone-600">
        No findings yet. Add one under <code className="text-xs">docs/findings/&lt;id&gt;/</code>.
      </p>
    </div>
  );
}
