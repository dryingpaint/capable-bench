import Link from 'next/link';
import { notFound } from 'next/navigation';
import { ArrowLeft, Calendar, FileText, ChevronDown } from 'lucide-react';
import { getFinding, formatBytes, type Artifact } from '@/lib/findings';
import Markdown from '@/components/Markdown';
import ArtifactView from '@/components/ArtifactView';

export const dynamic = 'force-dynamic';

interface PageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: PageProps) {
  const { id } = await params;
  const finding = await getFinding(id);
  return {
    title: finding ? `${finding.title} · Findings` : 'Finding · Capable Bench',
  };
}

export default async function FindingPage({ params }: PageProps) {
  const { id } = await params;
  const finding = await getFinding(id);

  if (!finding) {
    notFound();
  }

  return (
    <div className="min-h-screen bg-stone-50">
      <header className="bg-gradient-to-b from-stone-100 to-stone-50 border-b border-stone-200">
        <div className="max-w-5xl mx-auto px-8 py-8">
          <Link
            href="/findings"
            className="inline-flex items-center gap-1 text-sm text-stone-600 hover:text-stone-900 mb-4"
          >
            <ArrowLeft className="h-4 w-4" />
            All findings
          </Link>
          <div className="text-xs uppercase tracking-wider text-stone-600 font-semibold mb-2">
            Finding
          </div>
          <h1 className="text-3xl font-bold text-stone-900 mb-1">{finding.title}</h1>
          <div className="text-sm text-stone-500 font-mono mb-3">{finding.id}</div>
          <div className="flex items-center gap-4 text-xs text-stone-500">
            <span className="inline-flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              Last updated {new Date(finding.lastModified).toLocaleDateString()}
            </span>
            <span className="inline-flex items-center gap-1">
              <FileText className="h-3 w-3" />
              {finding.artifacts.length} artifact{finding.artifacts.length === 1 ? '' : 's'}
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-8 py-8 space-y-8">
        {finding.readme ? (
          <section className="bg-white border border-stone-200 rounded-lg px-6 py-6">
            <Markdown>{finding.readme}</Markdown>
          </section>
        ) : (
          <section className="bg-amber-50 border border-amber-200 rounded-lg px-6 py-4 text-sm text-amber-800">
            No <code className="text-xs">README.md</code> in this finding directory. The artifacts
            below are the raw inputs and outputs for this case.
          </section>
        )}

        {finding.artifacts.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold text-stone-900 mb-3">Artifacts</h2>
            <div className="space-y-2">
              {finding.artifacts.map((artifact) => (
                <ArtifactSection key={artifact.relativePath} artifact={artifact} />
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

function ArtifactSection({ artifact }: { artifact: Artifact }) {
  return (
    <details className="group border border-stone-200 rounded-lg bg-white overflow-hidden">
      <summary className="flex items-center justify-between gap-3 px-4 py-3 cursor-pointer hover:bg-stone-50 select-none">
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <KindBadge kind={artifact.kind} />
          <span className="font-mono text-sm text-stone-800 truncate">
            {artifact.relativePath}
          </span>
        </div>
        <div className="flex items-center gap-3 text-xs text-stone-500 shrink-0">
          <span>{formatBytes(artifact.size)}</span>
          <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" />
        </div>
      </summary>
      <div className="border-t border-stone-200">
        <ArtifactView artifact={artifact} />
      </div>
    </details>
  );
}

function KindBadge({ kind }: { kind: Artifact['kind'] }) {
  const styles: Record<Artifact['kind'], string> = {
    markdown: 'bg-blue-50 text-blue-700 border-blue-200',
    json: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    yaml: 'bg-violet-50 text-violet-700 border-violet-200',
    csv: 'bg-amber-50 text-amber-700 border-amber-200',
    text: 'bg-stone-100 text-stone-700 border-stone-200',
  };
  return (
    <span className={`inline-block text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded border ${styles[kind]}`}>
      {kind}
    </span>
  );
}
