'use client';

import { useState, useEffect } from 'react';
import type { ComponentType, ReactNode } from 'react';
import { ChevronLeft, ChevronRight, X, FileText, Calendar, Folder } from 'lucide-react';

// Dynamic import with fallback
let ReactMarkdown: ComponentType<{
  children: string;
  components?: Record<string, unknown>;
}> | null = null;
try {
  // Use dynamic import to handle missing dependency gracefully
  import('react-markdown').then(module => {
    ReactMarkdown = module.default;
  }).catch(() => {
    console.warn('react-markdown not available, using fallback renderer');
  });
} catch {
  console.warn('react-markdown import failed, using fallback renderer');
}

interface Finding {
  id: string;
  title: string;
  path: string;
  directory: string;
  filename: string;
  content: string;
  fullContent: string;
  lastModified: string;
}

interface FindingsViewerProps {
  onClose: () => void;
}

// Simple markdown-to-HTML fallback renderer
function SimpleMarkdownRenderer({ children }: { children: string }) {
  const html = children
    // Headers
    .replace(/^### (.*$)/gm, '<h3 class="text-lg font-medium text-stone-700 mb-2 mt-4">$1</h3>')
    .replace(/^## (.*$)/gm, '<h2 class="text-xl font-semibold text-stone-800 mb-3 mt-5">$1</h2>')
    .replace(/^# (.*$)/gm, '<h1 class="text-2xl font-bold text-stone-900 mb-4 mt-6">$1</h1>')
    // Bold text
    .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-stone-900">$1</strong>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code class="bg-stone-100 text-stone-800 px-1.5 py-0.5 rounded text-sm font-mono">$1</code>')
    // Code blocks
    .replace(/```[\s\S]*?```/g, (match) => {
      const code = match.slice(3, -3).trim();
      return `<pre class="bg-stone-50 border border-stone-200 rounded-lg p-4 overflow-x-auto my-4"><code class="text-sm font-mono">${code}</code></pre>`;
    })
    // Line breaks
    .replace(/\n\n/g, '</p><p class="mb-4">')
    .replace(/\n/g, '<br>');

  return (
    <div
      className="prose prose-stone prose-sm max-w-none"
      dangerouslySetInnerHTML={{ __html: `<p class="mb-4">${html}</p>` }}
    />
  );
}

export default function FindingsViewer({ onClose }: FindingsViewerProps) {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'list' | 'detail'>('list');
  const [markdownReady, setMarkdownReady] = useState(false);

  async function loadFindings() {
    try {
      const response = await fetch('/api/findings');
      if (!response.ok) {
        throw new Error('Failed to load findings');
      }
      const data = await response.json();
      setFindings(data.findings);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void Promise.resolve().then(loadFindings);

    // Try to load ReactMarkdown
    import('react-markdown').then(module => {
      ReactMarkdown = module.default;
      setMarkdownReady(true);
    }).catch(() => {
      console.warn('react-markdown not available, using fallback renderer');
      setMarkdownReady(false);
    });
  }, []);

  const currentFinding = findings[currentIndex];

  const nextFinding = () => {
    setCurrentIndex((prev) => (prev + 1) % findings.length);
  };

  const prevFinding = () => {
    setCurrentIndex((prev) => (prev - 1 + findings.length) % findings.length);
  };

  const selectFinding = (index: number) => {
    setCurrentIndex(index);
    setViewMode('detail');
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-xl p-8 text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-stone-900 mx-auto mb-4"></div>
          <p className="text-stone-600">Loading findings...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-xl p-8 text-center max-w-md">
          <div className="text-red-600 mb-4">
            <FileText className="h-8 w-8 mx-auto mb-2" />
            <p className="font-semibold">Error Loading Findings</p>
          </div>
          <p className="text-stone-600 mb-4">{error}</p>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-stone-900 text-white rounded-lg hover:bg-stone-700 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-6xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b border-stone-200">
          <div className="flex items-center gap-4">
            <h2 className="text-xl font-bold text-stone-900">Research Findings</h2>
            <span className="text-sm text-stone-500">
              {findings.length} finding{findings.length !== 1 ? 's' : ''} available
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setViewMode(viewMode === 'list' ? 'detail' : 'list')}
              className="px-3 py-1 text-sm bg-stone-100 hover:bg-stone-200 rounded transition-colors"
            >
              {viewMode === 'list' ? 'Detail View' : 'List View'}
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-stone-100 rounded-lg transition-colors"
            >
              <X className="h-5 w-5 text-stone-600" />
            </button>
          </div>
        </div>

        {viewMode === 'list' ? (
          /* List View */
          <div className="flex-1 overflow-auto p-6">
            <div className="grid gap-4">
              {findings.map((finding, index) => (
                <div
                  key={finding.id}
                  onClick={() => selectFinding(index)}
                  className="border border-stone-200 rounded-lg p-4 hover:border-stone-300 hover:shadow-sm transition-all cursor-pointer"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-stone-900 mb-2 truncate">
                        {finding.title}
                      </h3>
                      <div className="flex items-center gap-4 text-xs text-stone-500 mb-3">
                        <div className="flex items-center gap-1">
                          <Folder className="h-3 w-3" />
                          {finding.directory}
                        </div>
                        <div className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {new Date(finding.lastModified).toLocaleDateString()}
                        </div>
                      </div>
                      <div className="text-sm text-stone-600 line-clamp-3 prose prose-sm max-w-none">
                        {ReactMarkdown && markdownReady ? (
                          <ReactMarkdown>{`${finding.content.substring(0, 300)}...`}</ReactMarkdown>
                        ) : (
                          <SimpleMarkdownRenderer>{`${finding.content.substring(0, 300)}...`}</SimpleMarkdownRenderer>
                        )}
                      </div>
                    </div>
                    <ChevronRight className="h-5 w-5 text-stone-400 mt-1" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          /* Detail View */
          <>
            {/* Navigation */}
            <div className="flex items-center justify-between px-6 py-3 border-b border-stone-200 bg-stone-50">
              <button
                onClick={prevFinding}
                disabled={findings.length <= 1}
                className="flex items-center gap-2 px-3 py-2 text-sm bg-white border border-stone-200 rounded hover:bg-stone-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </button>

              <div className="text-center">
                <div className="text-sm font-medium text-stone-900">
                  {currentFinding?.title}
                </div>
                <div className="text-xs text-stone-500">
                  {currentIndex + 1} of {findings.length}
                  {currentFinding && (
                    <span className="ml-2">
                      · {currentFinding.directory}
                      · {new Date(currentFinding.lastModified).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>

              <button
                onClick={nextFinding}
                disabled={findings.length <= 1}
                className="flex items-center gap-2 px-3 py-2 text-sm bg-white border border-stone-200 rounded hover:bg-stone-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto p-6">
              {currentFinding ? (
                <article className="prose prose-stone prose-sm max-w-none">
                  {ReactMarkdown && markdownReady ? (
                    <ReactMarkdown
                      components={{
                        // Customize code blocks
                        code: ({inline, children}: { inline?: boolean; children?: ReactNode }) => {
                          return inline ? (
                            <code className="bg-stone-100 text-stone-800 px-1.5 py-0.5 rounded text-sm font-mono">
                              {children}
                            </code>
                          ) : (
                            <pre className="bg-stone-50 border border-stone-200 rounded-lg p-4 overflow-x-auto">
                              <code className="text-sm font-mono">
                                {children}
                              </code>
                            </pre>
                          );
                        },
                        // Customize headers
                        h1: ({children}: { children?: ReactNode }) => <h1 className="text-2xl font-bold text-stone-900 mb-4 mt-6">{children}</h1>,
                        h2: ({children}: { children?: ReactNode }) => <h2 className="text-xl font-semibold text-stone-800 mb-3 mt-5">{children}</h2>,
                        h3: ({children}: { children?: ReactNode }) => <h3 className="text-lg font-medium text-stone-700 mb-2 mt-4">{children}</h3>,
                        // Customize links
                        a: ({children, href}: { children?: ReactNode; href?: string }) => (
                          <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800 underline">
                            {children}
                          </a>
                        ),
                        // Customize blockquotes
                        blockquote: ({children}: { children?: ReactNode }) => (
                          <blockquote className="border-l-4 border-stone-300 pl-4 py-2 bg-stone-50 text-stone-700 italic">
                            {children}
                          </blockquote>
                        ),
                      }}
                    >
                      {currentFinding.fullContent}
                    </ReactMarkdown>
                  ) : (
                    <SimpleMarkdownRenderer>
                      {currentFinding.fullContent}
                    </SimpleMarkdownRenderer>
                  )}
                </article>
              ) : (
                <div className="text-center text-stone-500 py-12">
                  No finding selected
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
