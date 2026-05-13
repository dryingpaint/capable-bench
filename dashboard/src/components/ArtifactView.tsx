import type { Artifact } from '@/lib/findings';
import Markdown from '@/components/Markdown';

interface ArtifactViewProps {
  artifact: Artifact;
  findingId: string;
}

export default function ArtifactView({ artifact, findingId }: ArtifactViewProps) {
  if (artifact.kind === 'image') {
    return <ImageView findingId={findingId} relativePath={artifact.relativePath} />;
  }

  if (artifact.kind === 'markdown') {
    return (
      <div className="px-4 py-3 bg-white">
        <Markdown findingId={findingId}>{artifact.content}</Markdown>
        {artifact.truncated && <TruncationNote />}
      </div>
    );
  }

  if (artifact.kind === 'json') {
    return <JsonView text={artifact.content} truncated={artifact.truncated} />;
  }

  if (artifact.kind === 'csv') {
    return <CsvView text={artifact.content} truncated={artifact.truncated} />;
  }

  return <RawView text={artifact.content} truncated={artifact.truncated} />;
}

function JsonView({ text, truncated }: { text: string; truncated: boolean }) {
  let formatted = text;
  try {
    formatted = JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    // leave as-is when the content can't be parsed (e.g. JSON-Lines)
  }
  return (
    <div className="px-4 py-3 bg-stone-50">
      <pre className="text-xs font-mono text-stone-800 overflow-x-auto max-h-[60vh]">{formatted}</pre>
      {truncated && <TruncationNote />}
    </div>
  );
}

function CsvView({ text, truncated }: { text: string; truncated: boolean }) {
  const rows = parseCsv(text);
  if (rows.length === 0) {
    return <RawView text={text} truncated={truncated} />;
  }
  const [header, ...body] = rows;
  return (
    <div className="px-4 py-3 bg-white">
      <div className="overflow-x-auto max-h-[60vh] border border-stone-200">
        <table className="min-w-full text-xs">
          <thead className="bg-stone-100 sticky top-0">
            <tr>
              {header.map((cell, i) => (
                <th key={i} className="border-b border-stone-200 px-3 py-2 text-left font-semibold text-stone-700">
                  {cell}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {body.map((row, ri) => (
              <tr key={ri} className={ri % 2 === 0 ? 'bg-white' : 'bg-stone-50'}>
                {row.map((cell, ci) => (
                  <td key={ci} className="border-b border-stone-100 px-3 py-1.5 text-stone-800 align-top">
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-2 text-xs text-stone-500">{body.length} row{body.length === 1 ? '' : 's'}</div>
      {truncated && <TruncationNote />}
    </div>
  );
}

function RawView({ text, truncated }: { text: string; truncated: boolean }) {
  return (
    <div className="px-4 py-3 bg-stone-50">
      <pre className="text-xs font-mono text-stone-800 overflow-x-auto whitespace-pre-wrap max-h-[60vh]">
        {text}
      </pre>
      {truncated && <TruncationNote />}
    </div>
  );
}

function ImageView({ findingId, relativePath }: { findingId: string; relativePath: string }) {
  const src = `/finding-files/${encodeURIComponent(findingId)}/${relativePath
    .split('/')
    .map(encodeURIComponent)
    .join('/')}`;
  return (
    <div className="px-4 py-3 bg-white flex justify-center">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={relativePath}
        className="max-w-full h-auto border border-stone-200"
      />
    </div>
  );
}

function TruncationNote() {
  return (
    <div className="mt-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 px-2 py-1 inline-block">
      File truncated — preview only.
    </div>
  );
}

function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let field = '';
  let row: string[] = [];
  let quoted = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];

    if (quoted) {
      if (char === '"' && next === '"') {
        field += '"';
        i += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        field += char;
      }
      continue;
    }

    if (char === '"') {
      quoted = true;
    } else if (char === ',') {
      row.push(field);
      field = '';
    } else if (char === '\n') {
      row.push(field);
      rows.push(row);
      row = [];
      field = '';
    } else if (char !== '\r') {
      field += char;
    }
  }

  if (field || row.length) {
    row.push(field);
    rows.push(row);
  }

  return rows.filter((r) => r.some((cell) => cell.length > 0));
}
