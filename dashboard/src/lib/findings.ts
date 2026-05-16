import path from 'path';
import fs from 'fs/promises';
import { listTaskIds } from '@/lib/tasks';

const FINDINGS_DIR = path.resolve(process.cwd(), '..', 'docs', 'findings');
const SUMMARY_BYTES = 2000;
const SAFE_ID = /^[A-Za-z0-9._-]+$/;
const ARTIFACT_BYTE_LIMIT = 512 * 1024;

export type ArtifactKind = 'markdown' | 'json' | 'yaml' | 'csv' | 'text' | 'image';

const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.avif'];

export interface Artifact {
  name: string;
  relativePath: string;
  size: number;
  kind: ArtifactKind;
  content: string;
  truncated: boolean;
}

export interface FindingSummary {
  id: string;
  title: string;
  preview: string;
  lastModified: string;
  artifactCount: number;
}

export interface Finding {
  id: string;
  title: string;
  readme: string | null;
  readmeFilename: string | null;
  lastModified: string;
  artifacts: Artifact[];
  linkedTaskIds: string[];
}

export async function listFindings(): Promise<FindingSummary[]> {
  const entries = await safeReadDir(FINDINGS_DIR);
  const results: FindingSummary[] = [];

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    if (!SAFE_ID.test(entry.name)) continue;

    const dirPath = path.join(FINDINGS_DIR, entry.name);
    const { readmePath, readmeFilename } = await findReadme(dirPath);
    const dirStat = await fs.stat(dirPath);

    let title = entry.name;
    let preview = '';
    let lastModified = dirStat.mtime.toISOString();

    if (readmePath) {
      const text = await readBoundedText(readmePath, SUMMARY_BYTES);
      title = extractTitle(text) ?? entry.name;
      preview = extractPreview(text);
      const stat = await fs.stat(readmePath);
      lastModified = stat.mtime.toISOString();
    }

    const artifactCount = await countArtifacts(dirPath, readmeFilename);

    results.push({
      id: entry.name,
      title,
      preview,
      lastModified,
      artifactCount,
    });
  }

  results.sort((a, b) => b.lastModified.localeCompare(a.lastModified));
  return results;
}

export async function getFinding(id: string): Promise<Finding | null> {
  if (!SAFE_ID.test(id)) return null;

  const dirPath = path.join(FINDINGS_DIR, id);
  const dirStat = await safeStat(dirPath);
  if (!dirStat || !dirStat.isDirectory()) return null;

  const { readmePath, readmeFilename } = await findReadme(dirPath);
  let readme: string | null = null;
  let title = id;
  let lastModified = dirStat.mtime.toISOString();

  if (readmePath) {
    readme = await fs.readFile(readmePath, 'utf-8');
    title = extractTitle(readme) ?? id;
    const stat = await fs.stat(readmePath);
    lastModified = stat.mtime.toISOString();
  }

  const artifacts = await collectArtifacts(dirPath, dirPath, readmeFilename);
  artifacts.sort((a, b) => a.relativePath.localeCompare(b.relativePath));

  const knownTaskIds = new Set(await listTaskIds());
  const linkedTaskIds = resolveLinkedTaskIds(id, readme, knownTaskIds);

  return {
    id,
    title,
    readme,
    readmeFilename,
    lastModified,
    artifacts,
    linkedTaskIds,
  };
}

function resolveLinkedTaskIds(
  findingId: string,
  readme: string | null,
  knownTaskIds: Set<string>,
): string[] {
  const ids = new Set<string>();
  if (knownTaskIds.has(findingId)) ids.add(findingId);
  if (readme) {
    // Match lines like "**Task:** `task-id`" or "**Task ID:** `task-id`" — the
    // pattern findings have been using to point at their canonical benchmark
    // problem when the finding dir name doesn't match the task ID directly.
    const pattern = /\*\*Task(?:\s+ID)?:\*\*\s+`([^`]+)`/g;
    let match: RegExpExecArray | null;
    while ((match = pattern.exec(readme)) !== null) {
      const candidate = match[1].trim();
      if (knownTaskIds.has(candidate)) ids.add(candidate);
    }
  }
  return [...ids];
}

async function findReadme(dirPath: string): Promise<{ readmePath: string | null; readmeFilename: string | null }> {
  const candidates = ['README.md', 'readme.md'];
  for (const name of candidates) {
    const candidate = path.join(dirPath, name);
    if (await exists(candidate)) {
      return { readmePath: candidate, readmeFilename: name };
    }
  }
  return { readmePath: null, readmeFilename: null };
}

async function countArtifacts(dirPath: string, readmeFilename: string | null): Promise<number> {
  const entries = await safeReadDir(dirPath);
  let count = 0;
  for (const entry of entries) {
    if (entry.isDirectory()) {
      count += await countArtifacts(path.join(dirPath, entry.name), null);
      continue;
    }
    if (entry.isFile() && entry.name !== readmeFilename) {
      count += 1;
    }
  }
  return count;
}

async function collectArtifacts(
  rootDir: string,
  currentDir: string,
  readmeFilename: string | null,
): Promise<Artifact[]> {
  const entries = await safeReadDir(currentDir);
  const artifacts: Artifact[] = [];

  for (const entry of entries) {
    const fullPath = path.join(currentDir, entry.name);
    if (entry.isDirectory()) {
      const nested = await collectArtifacts(rootDir, fullPath, null);
      artifacts.push(...nested);
      continue;
    }
    if (!entry.isFile()) continue;
    if (currentDir === rootDir && entry.name === readmeFilename) continue;

    const stat = await fs.stat(fullPath);
    const kind = classifyArtifact(entry.name);
    const content =
      kind === 'image'
        ? ''
        : await readBoundedText(fullPath, Math.min(stat.size, ARTIFACT_BYTE_LIMIT));

    artifacts.push({
      name: entry.name,
      relativePath: path.relative(rootDir, fullPath),
      size: stat.size,
      kind,
      content,
      truncated: kind !== 'image' && stat.size > ARTIFACT_BYTE_LIMIT,
    });
  }

  return artifacts;
}

function classifyArtifact(name: string): ArtifactKind {
  const lower = name.toLowerCase();
  if (lower.endsWith('.md')) return 'markdown';
  if (lower.endsWith('.json')) return 'json';
  if (lower.endsWith('.yaml') || lower.endsWith('.yml')) return 'yaml';
  if (lower.endsWith('.csv') || lower.endsWith('.tsv')) return 'csv';
  if (IMAGE_EXTENSIONS.some((ext) => lower.endsWith(ext))) return 'image';
  return 'text';
}

function extractTitle(text: string): string | null {
  for (const line of text.split('\n')) {
    const match = line.match(/^#\s+(.*\S)\s*$/);
    if (match) return match[1];
  }
  return null;
}

function extractPreview(text: string): string {
  const stripped = text
    .split('\n')
    .filter((line) => !line.startsWith('#'))
    .map((line) => line.replace(/[^\S\n]+/g, ' ').trim())
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
  return stripped.slice(0, 240) + (stripped.length > 240 ? '…' : '');
}

async function readBoundedText(filePath: string, maxBytes: number): Promise<string> {
  if (maxBytes <= 0) return '';
  const handle = await fs.open(filePath, 'r');
  try {
    const buffer = Buffer.alloc(maxBytes);
    const { bytesRead } = await handle.read(buffer, 0, maxBytes, 0);
    return buffer.subarray(0, bytesRead).toString('utf-8');
  } finally {
    await handle.close();
  }
}

async function exists(filePath: string): Promise<boolean> {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function safeStat(filePath: string) {
  try {
    return await fs.stat(filePath);
  } catch {
    return null;
  }
}

async function safeReadDir(dirPath: string) {
  try {
    return await fs.readdir(dirPath, { withFileTypes: true });
  } catch {
    return [];
  }
}

export function formatBytes(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}
