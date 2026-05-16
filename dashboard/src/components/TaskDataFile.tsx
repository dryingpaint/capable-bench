'use client';

import { useEffect, useState } from 'react';
import { ChevronDown } from 'lucide-react';

interface TaskDataFileProps {
  taskId: string;
  name: string;
  sizeBytes: number;
}

type Kind = 'json' | 'yaml' | 'csv' | 'markdown' | 'image' | 'text';

const IMAGE_EXT = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.avif'];

function classify(name: string): Kind {
  const lower = name.toLowerCase();
  if (lower.endsWith('.json')) return 'json';
  if (lower.endsWith('.yaml') || lower.endsWith('.yml')) return 'yaml';
  if (lower.endsWith('.csv') || lower.endsWith('.tsv')) return 'csv';
  if (lower.endsWith('.md')) return 'markdown';
  if (IMAGE_EXT.some((ext) => lower.endsWith(ext))) return 'image';
  return 'text';
}

function formatBytes(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function kindBadgeStyle(kind: Kind): string {
  switch (kind) {
    case 'csv':
      return 'bg-amber-50 text-amber-700 border-amber-200';
    case 'json':
      return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    case 'yaml':
      return 'bg-violet-50 text-violet-700 border-violet-200';
    case 'markdown':
      return 'bg-blue-50 text-blue-700 border-blue-200';
    case 'image':
      return 'bg-pink-50 text-pink-700 border-pink-200';
    default:
      return 'bg-stone-100 text-stone-700 border-stone-200';
  }
}

export default function TaskDataFile({ taskId, name, sizeBytes }: TaskDataFileProps) {
  const kind = classify(name);
  const fileUrl = `/task-files/${encodeURIComponent(taskId)}/${encodeURIComponent(name)}`;
  const [open, setOpen] = useState(false);
  const [text, setText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || kind === 'image' || text !== null) return;
    let cancelled = false;
    async function load() {
      try {
        setLoading(true);
        const response = await fetch(fileUrl);
        if (!response.ok) throw new Error('Failed to load file');
        const body = await response.text();
        if (!cancelled) {
          setText(body);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [open, kind, fileUrl, text]);

  return (
    <details
      className="group border border-stone-200 bg-white overflow-hidden"
      onToggle={(event) => setOpen((event.target as HTMLDetailsElement).open)}
    >
      <summary className="flex items-center justify-between gap-3 px-4 py-3 cursor-pointer hover:bg-stone-50 select-none">
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <span
            className={`inline-block text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 border ${kindBadgeStyle(kind)}`}
          >
            {kind}
          </span>
          <span className="font-mono text-sm text-stone-800 truncate">{name}</span>
        </div>
        <div className="flex items-center gap-3 text-xs text-stone-500 shrink-0">
          <a
            href={fileUrl}
            download={name}
            onClick={(event) => event.stopPropagation()}
            className="hover:text-stone-900 underline"
          >
            download
          </a>
          <span>{formatBytes(sizeBytes)}</span>
          <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" />
        </div>
      </summary>
      <div className="border-t border-stone-200">
        {kind === 'image' ? (
          <div className="px-4 py-3 bg-white flex justify-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={fileUrl} alt={name} className="max-w-full h-auto border border-stone-200" />
          </div>
        ) : loading ? (
          <div className="px-4 py-3 text-sm text-stone-500">Loading…</div>
        ) : error ? (
          <div className="px-4 py-3 text-sm text-red-600">{error}</div>
        ) : text === null ? null : kind === 'csv' ? (
          <CsvView text={text} />
        ) : kind === 'json' ? (
          <JsonView text={text} />
        ) : (
          <RawView text={text} />
        )}
      </div>
    </details>
  );
}

function JsonView({ text }: { text: string }) {
  let formatted = text;
  try {
    formatted = JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    // leave as-is
  }
  return (
    <div className="px-4 py-3 bg-stone-50">
      <pre className="text-xs font-mono text-stone-800 overflow-x-auto max-h-[60vh]">{formatted}</pre>
    </div>
  );
}

function RawView({ text }: { text: string }) {
  return (
    <div className="px-4 py-3 bg-stone-50">
      <pre className="text-xs font-mono text-stone-800 overflow-x-auto whitespace-pre-wrap max-h-[60vh]">{text}</pre>
    </div>
  );
}

function CsvView({ text }: { text: string }) {
  const rows = parseCsv(text);
  if (rows.length === 0) return <RawView text={text} />;
  const [header, ...body] = rows;
  return (
    <div className="px-4 py-3 bg-white">
      <div className="overflow-x-auto max-h-[60vh] border border-stone-200">
        <table className="min-w-full text-xs">
          <thead className="bg-stone-100 sticky top-0">
            <tr>
              {header.map((cell, i) => (
                <th
                  key={i}
                  className="border-b border-stone-200 px-3 py-2 text-left font-semibold text-stone-700"
                >
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
      <div className="mt-2 text-xs text-stone-500">
        {body.length} row{body.length === 1 ? '' : 's'}
      </div>
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
