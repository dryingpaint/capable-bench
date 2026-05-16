'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';

interface MarkdownProps {
  children: string;
  /**
   * Finding id used to resolve relative image URLs (e.g. `./chart.png`) against
   * the `/api/findings/<id>/file/...` route. Omit for markdown rendered outside
   * a finding context — relative URLs will then be left as-is.
   */
  findingId?: string;
}

function resolveImageUrl(href: string | undefined, findingId: string | undefined): string | undefined {
  if (!href) return href;
  if (/^(https?:)?\/\//i.test(href) || href.startsWith('data:')) return href;
  if (!findingId) return href;
  const stripped = href.replace(/^\.?\/+/, '');
  if (stripped.startsWith('..') || stripped === '') return href;
  const encoded = stripped.split('/').map(encodeURIComponent).join('/');
  return `/finding-files/${encodeURIComponent(findingId)}/${encoded}`;
}

function isLocalFindingRef(href: string | undefined): boolean {
  if (!href) return false;
  if (/^(https?:)?\/\//i.test(href) || href.startsWith('data:') || href.startsWith('mailto:') || href.startsWith('#')) return false;
  const stripped = href.replace(/^\.?\/+/, '');
  return !stripped.startsWith('..') && stripped.length > 0;
}

const TRACE_FIELD_LIMIT = 800;

function trunc(value: unknown, limit = TRACE_FIELD_LIMIT): string {
  const text = typeof value === 'string' ? value : JSON.stringify(value);
  if (!text) return '';
  return text.length > limit ? `${text.slice(0, limit)}… (+${text.length - limit} chars)` : text;
}

// Format a Claude `tool_use` block with the most useful inputs surfaced first
// (especially for WebSearch / Agent / Read / Bash so they're visually distinct).
function formatClaudeToolUse(block: Record<string, unknown>): string {
  const name = String(block.name ?? '?');
  const input = (block.input as Record<string, unknown>) || {};
  switch (name) {
    case 'WebSearch':
    case 'WebFetch': {
      const q = input.query ?? input.url ?? '';
      return `[🔍 ${name}] "${trunc(q, 200)}"`;
    }
    case 'Read': {
      const path = input.file_path ?? input.path ?? '';
      const offset = input.offset ?? null;
      const limit = input.limit ?? null;
      const range = offset !== null || limit !== null ? ` (offset=${offset ?? 0}, limit=${limit ?? '∞'})` : '';
      return `[📄 Read] ${trunc(path, 200)}${range}`;
    }
    case 'Write': {
      return `[✏️ Write] ${trunc(input.file_path ?? input.path ?? '', 200)}`;
    }
    case 'Edit': {
      return `[✏️ Edit] ${trunc(input.file_path ?? input.path ?? '', 200)}`;
    }
    case 'Bash': {
      const cmd = input.command ?? '';
      const desc = input.description ? ` # ${trunc(input.description, 100)}` : '';
      return `[🛠 Bash] ${trunc(cmd, 300)}${desc}`;
    }
    case 'Glob':
    case 'Grep': {
      const pattern = input.pattern ?? input.glob ?? '';
      const target = input.path ? ` in ${input.path}` : '';
      return `[🔎 ${name}] ${trunc(pattern, 200)}${target}`;
    }
    case 'Agent': {
      const desc = input.description ?? '';
      const subtype = input.subagent_type ? ` (${input.subagent_type})` : '';
      return `[🤖 Agent${subtype}] ${trunc(desc, 200)}`;
    }
    case 'ToolSearch': {
      return `[🧰 ToolSearch] ${trunc(input.query ?? '', 200)}`;
    }
    default:
      return `[tool_call] ${name}(${trunc(input, 400)})`;
  }
}

// Port of capablebench/run.py:_format_agent_event — renders a single
// stream-json event (Claude or Codex) into a human-readable line.
function formatAgentEvent(event: Record<string, unknown>): string {
  const et = event.type;
  // Claude stream-json
  if (et === 'system') {
    const sub = (event.subtype as string) || '';
    const model = (event.model as string) || '';
    const tag = sub ? `system:${sub}` : 'system';
    return `[${tag}]${model ? ` model=${model}` : ''}`;
  }
  if (et === 'assistant') {
    const msg = (event.message as Record<string, unknown>) || {};
    const blocks = (msg.content as Array<Record<string, unknown>>) || [];
    const out: string[] = [];
    for (const b of blocks) {
      if (b.type === 'text') out.push(`[assistant] ${trunc(b.text)}`);
      else if (b.type === 'tool_use') out.push(formatClaudeToolUse(b));
      else if (b.type === 'thinking') out.push(`[thinking] ${trunc(b.thinking ?? b.text ?? '')}`);
    }
    return out.join('\n');
  }
  if (et === 'user') {
    const msg = (event.message as Record<string, unknown>) || {};
    const content = msg.content;
    if (!Array.isArray(content)) return '';
    const out: string[] = [];
    for (const b of content as Array<Record<string, unknown>>) {
      if (b.type !== 'tool_result') continue;
      let inner = b.content;
      if (Array.isArray(inner)) {
        inner = (inner as Array<Record<string, unknown>>)
          .map((c) => (typeof c === 'object' && c && 'text' in c ? String(c.text) : String(c)))
          .join('');
      }
      out.push(`[tool_result] ${trunc(inner)}`);
    }
    return out.join('\n');
  }
  if (et === 'result') {
    const usage = (event.usage as Record<string, unknown>) || {};
    return `[result:${event.subtype ?? ''}] cost=$${event.total_cost_usd ?? '?'} duration=${event.duration_ms ?? '?'}ms tokens(in=${usage.input_tokens ?? '?'} out=${usage.output_tokens ?? '?'})`;
  }
  // Codex exec --json
  if (et === 'thread.started') return `[codex] thread_started id=${event.thread_id ?? ''}`;
  if (et === 'turn.started') return '[codex] turn_started';
  if (et === 'turn.completed') {
    const usage = (event.usage as Record<string, unknown>) || {};
    return `[codex] turn_completed tokens(in=${usage.input_tokens ?? '?'} out=${usage.output_tokens ?? '?'} reasoning=${usage.reasoning_output_tokens ?? '?'})`;
  }
  if (et === 'item.completed') {
    const item = (event.item as Record<string, unknown>) || {};
    const itype = item.type;
    if (itype === 'agent_message') return `[assistant] ${trunc(item.text ?? item.message ?? '')}`;
    if (itype === 'reasoning') return `[reasoning] ${trunc(item.text ?? '')}`;
    if (itype === 'command_execution') {
      let cmd: unknown = item.command;
      if (Array.isArray(cmd)) cmd = (cmd as unknown[]).join(' ');
      const out = item.aggregated_output ?? item.output ?? '';
      return `[🛠 exec] ${trunc(cmd ?? '', 300)}\n        ↳ exit=${item.exit_code ?? '?'} ${trunc(out, 600)}`;
    }
    if (itype === 'web_search') {
      const action = (item.action as Record<string, unknown>) || {};
      const queries = (action.queries as string[]) || (action.query ? [String(action.query)] : []);
      const q = queries.length > 0 ? queries[0] : (item.query as string) || '';
      const more = queries.length > 1 ? `  (+${queries.length - 1} more queries)` : '';
      return `[🔍 web_search] "${trunc(q, 200)}"${more}`;
    }
    if (itype === 'web_fetch' || itype === 'webfetch') {
      return `[🔍 web_fetch] ${trunc(item.url ?? '', 200)}`;
    }
    if (itype === 'mcp_tool_use' || itype === 'mcp_tool_call') {
      const server = item.server ?? '';
      const tool = item.tool ?? item.name ?? '';
      return `[🧩 mcp:${server}/${tool}] ${trunc(item.input ?? item.arguments ?? '', 200)}`;
    }
    if (itype === 'file_change') {
      const changes = (item.changes as Array<Record<string, unknown>>) || [];
      const summary = changes.map((c) => `${c.kind ?? '?'} ${c.path ?? '?'}`).join(', ');
      return `[✏️ file_change] ${summary}`;
    }
    if (itype) {
      const { type: _t, ...rest } = item as { type?: unknown };
      void _t;
      return `[${String(itype)}] ${trunc(rest)}`;
    }
  }
  if (et === 'item.started') return '';
  if (et === 'error') return `[error] ${trunc(event.message ?? event)}`;
  return '';
}

function renderAgentTraceJsonl(text: string): string | null {
  // Heuristic: detect JSONL by requiring most non-empty lines to start with `{`
  const lines = text.split(/\r?\n/);
  const nonEmpty = lines.filter((l) => l.trim().length > 0);
  if (nonEmpty.length === 0) return null;
  const jsonish = nonEmpty.filter((l) => l.trim().startsWith('{'));
  if (jsonish.length / nonEmpty.length < 0.8) return null;

  const out: string[] = [];
  for (const raw of nonEmpty) {
    try {
      const event = JSON.parse(raw) as Record<string, unknown>;
      const rendered = formatAgentEvent(event);
      if (rendered) out.push(rendered);
    } catch {
      // Skip unparseable lines (keep going — partial JSONL is still useful)
    }
  }
  return out.length > 0 ? out.join('\n') : null;
}

function LocalFileToggle({
  href,
  label,
  findingId,
}: {
  href: string;
  label: ReactNode;
  findingId: string;
}) {
  const [open, setOpen] = useState(false);
  const [content, setContent] = useState<string | null>(null);
  const [renderedTrace, setRenderedTrace] = useState<string | null>(null);
  const [showRaw, setShowRaw] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const url = resolveImageUrl(href, findingId);

  useEffect(() => {
    if (!open || content !== null || error !== null || !url) return;
    let cancelled = false;
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.text();
      })
      .then((text) => {
        if (cancelled) return;
        setContent(text);
        setRenderedTrace(renderAgentTraceJsonl(text));
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [open, url, content, error]);

  const displayed = showRaw || !renderedTrace ? content : renderedTrace;

  return (
    <details
      className="my-2 border border-stone-200 bg-stone-50 text-sm"
      onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}
    >
      <summary className="cursor-pointer px-3 py-1.5 hover:bg-stone-100 select-none flex items-center gap-2">
        <span>{label}</span>
        <span className="text-xs text-stone-400 font-mono">{href}</span>
      </summary>
      <div className="p-3 border-t border-stone-200">
        {error && <div className="text-xs text-red-600">Failed to load: {error}</div>}
        {!content && !error && <div className="text-xs text-stone-500">Loading…</div>}
        {content && renderedTrace && (
          <div className="mb-2 text-xs">
            <button
              type="button"
              onClick={() => setShowRaw((v) => !v)}
              className="text-stone-500 hover:text-stone-900 underline"
            >
              {showRaw ? 'Show rendered trace' : 'Show raw JSONL'}
            </button>
          </div>
        )}
        {displayed && (
          <pre className="text-xs font-mono whitespace-pre-wrap overflow-auto max-h-96 text-stone-800">
            {displayed}
          </pre>
        )}
      </div>
    </details>
  );
}

type MarkdownNode = {
  type?: string;
  value?: string;
  children?: MarkdownNode[];
  [key: string]: unknown;
};

function remarkPreserveNewlines() {
  return (tree: MarkdownNode) => {
    transformNewlines(tree);
  };
}

function transformNewlines(node: MarkdownNode) {
  if (!node.children) {
    return;
  }

  const children: MarkdownNode[] = [];
  for (const child of node.children) {
    if (child.type === 'text' && child.value?.includes('\n')) {
      const parts = child.value.split('\n');
      parts.forEach((part, index) => {
        if (index > 0) {
          children.push({ type: 'break' });
        }
        if (part) {
          children.push({ ...child, value: part });
        }
      });
      continue;
    }

    transformNewlines(child);
    children.push(child);
  }

  node.children = children;
}

export default function Markdown({ children, findingId }: MarkdownProps) {
  return (
    <div className="markdown-body text-sm text-stone-800 leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkPreserveNewlines]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-2xl font-bold text-stone-900 mt-6 mb-4 first:mt-0">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-xl font-semibold text-stone-900 mt-6 mb-3 pb-1 border-b border-stone-200">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-lg font-semibold text-stone-800 mt-5 mb-2">{children}</h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-base font-semibold text-stone-800 mt-4 mb-2">{children}</h4>
          ),
          p: ({ children }) => <p className="my-3">{children}</p>,
          strong: ({ children }) => <strong className="font-semibold text-stone-900">{children}</strong>,
          em: ({ children }) => <em className="italic">{children}</em>,
          ul: ({ children }) => <ul className="my-3 ml-6 list-disc space-y-1">{children}</ul>,
          ol: ({ children }) => <ol className="my-3 ml-6 list-decimal space-y-1">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          a: ({ children, href }) => {
            // Absolute site paths (/tasks/..., /findings/...) are internal
            // navigation, NOT in-finding file refs — check this before the
            // local-finding-ref handler swallows them.
            if (typeof href === 'string' && href.startsWith('/')) {
              return (
                <Link href={href} className="text-blue-600 hover:text-blue-800 underline">
                  {children}
                </Link>
              );
            }
            if (findingId && typeof href === 'string' && isLocalFindingRef(href)) {
              return <LocalFileToggle href={href} label={children} findingId={findingId} />;
            }
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 underline"
              >
                {children}
              </a>
            );
          },
          img: ({ src, alt, title }) => {
            const resolved = resolveImageUrl(typeof src === 'string' ? src : undefined, findingId);
            // eslint-disable-next-line @next/next/no-img-element
            return (
              <img
                src={resolved}
                alt={alt ?? ''}
                title={title}
                className="my-4 max-w-full h-auto border border-stone-200"
              />
            );
          },
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-stone-300 pl-4 py-1 my-3 bg-stone-50 text-stone-700 italic">
              {children}
            </blockquote>
          ),
          hr: () => <hr className="my-6 border-stone-200" />,
          pre: ({ children }: { children?: ReactNode }) => (
            <pre className="bg-stone-50 border border-stone-200 p-4 overflow-x-auto my-4 text-xs font-mono text-stone-800">
              {children}
            </pre>
          ),
          code: ({ className, children }) => {
            const isBlock = typeof className === 'string' && className.startsWith('language-');
            if (isBlock) {
              return <code className={className}>{children}</code>;
            }
            return (
              <code className="bg-stone-100 text-stone-800 px-1.5 py-0.5 text-[0.85em] font-mono">
                {children}
              </code>
            );
          },
          table: ({ children }) => (
            <div className="overflow-x-auto my-4">
              <table className="min-w-full text-sm border border-stone-200 border-collapse">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-stone-100">{children}</thead>,
          tbody: ({ children }) => <tbody>{children}</tbody>,
          tr: ({ children }) => <tr className="border-b border-stone-200 last:border-b-0">{children}</tr>,
          th: ({ children }) => (
            <th className="border border-stone-200 px-3 py-2 text-left font-semibold text-stone-700">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-stone-200 px-3 py-2 align-top text-stone-800">{children}</td>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
