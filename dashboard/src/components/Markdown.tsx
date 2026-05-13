'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ReactNode } from 'react';

interface MarkdownProps {
  children: string;
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

export default function Markdown({ children }: MarkdownProps) {
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
          a: ({ children, href }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-800 underline"
            >
              {children}
            </a>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-stone-300 pl-4 py-1 my-3 bg-stone-50 text-stone-700 italic">
              {children}
            </blockquote>
          ),
          hr: () => <hr className="my-6 border-stone-200" />,
          pre: ({ children }: { children?: ReactNode }) => (
            <pre className="bg-stone-50 border border-stone-200 rounded-lg p-4 overflow-x-auto my-4 text-xs font-mono text-stone-800">
              {children}
            </pre>
          ),
          code: ({ className, children }) => {
            const isBlock = typeof className === 'string' && className.startsWith('language-');
            if (isBlock) {
              return <code className={className}>{children}</code>;
            }
            return (
              <code className="bg-stone-100 text-stone-800 px-1.5 py-0.5 rounded text-[0.85em] font-mono">
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
