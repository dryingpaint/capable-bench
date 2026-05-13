import Link from 'next/link';
import { notFound } from 'next/navigation';
import { ArrowLeft, Calendar, FileText, ChevronDown } from 'lucide-react';
import { getFinding, listFindings, formatBytes, type Artifact } from '@/lib/findings';
import Markdown from '@/components/Markdown';
import ArtifactView from '@/components/ArtifactView';

export const dynamicParams = false;

interface PageProps {
  params: Promise<{ id: string }>;
}

export async function generateStaticParams() {
  const findings = await listFindings();
  return findings.map((finding) => ({ id: finding.id }));
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
      <header className="border-b border-stone-200">
        <div className="max-w-5xl mx-auto px-8 py-6">
          <Link
            href="/findings"
            className="inline-flex items-center gap-1 text-sm text-stone-500 hover:text-stone-900 mb-3"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            All reports
          </Link>
          <h1 className="text-2xl font-semibold text-stone-900">{finding.title}</h1>
          <div className="text-xs text-stone-400 font-mono mt-1">{finding.id}</div>
          <div className="flex items-center gap-4 text-xs text-stone-500 mt-3">
            <span className="inline-flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {new Date(finding.lastModified).toLocaleDateString()}
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
          <section className="bg-white border border-stone-200 px-6 py-6">
            <Markdown findingId={finding.id}>{finding.readme}</Markdown>
          </section>
        ) : (
          <section className="bg-amber-50 border border-amber-200 px-6 py-4 text-sm text-amber-800">
            No <code className="text-xs">README.md</code> in this finding directory. The artifacts
            below are the raw inputs and outputs for this case.
          </section>
        )}

        {finding.artifacts.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold text-stone-900 mb-3">Artifacts</h2>
            <div className="space-y-2">
              {finding.artifacts.map((artifact) => (
                <ArtifactSection
                  key={artifact.relativePath}
                  artifact={artifact}
                  findingId={finding.id}
                />
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

function ArtifactSection({ artifact, findingId }: { artifact: Artifact; findingId: string }) {
  return (
    <details className="group border border-stone-200 bg-white overflow-hidden">
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
        <ArtifactView artifact={artifact} findingId={findingId} />
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
    image: 'bg-pink-50 text-pink-700 border-pink-200',
    text: 'bg-stone-100 text-stone-700 border-stone-200',
  };
  return (
    <span className={`inline-block text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 border ${styles[kind]}`}>
      {kind}
    </span>
  );
}
