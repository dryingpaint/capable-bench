import { NextRequest, NextResponse } from 'next/server';
import path from 'path';
import fs from 'fs/promises';

const MAX_ARTIFACT_BYTES = 256 * 1024;

export async function GET(request: NextRequest) {
  try {
    const capableBenchDir = path.resolve(process.cwd(), '..');
    const runsDir = path.join(capableBenchDir, 'runs');
    const taskId = request.nextUrl.searchParams.get('taskId') || '';
    const runId = request.nextUrl.searchParams.get('runId') || '';

    if (!isSafeSegment(taskId) || !isSafeSegment(runId)) {
      return NextResponse.json({ error: 'Invalid taskId or runId' }, { status: 400 });
    }

    const runDir = path.join(runsDir, taskId, runId);
    const resolvedRunDir = path.resolve(runDir);
    if (!resolvedRunDir.startsWith(path.resolve(runsDir) + path.sep)) {
      return NextResponse.json({ error: 'Invalid run path' }, { status: 400 });
    }

    const summary = await readJsonOptional(path.join(resolvedRunDir, 'run_summary.json'));
    if (!summary) {
      return NextResponse.json({ error: 'Run summary not found' }, { status: 404 });
    }

    const stdoutFile = artifactPath(resolvedRunDir, summary.stdout_file, 'stdout.txt');
    const stderrFile = artifactPath(resolvedRunDir, summary.stderr_file, 'stderr.txt');
    const traceFile = artifactPath(resolvedRunDir, summary.trace_file, 'agent_trace.txt');
    const answerFile = artifactPath(resolvedRunDir, summary.answer_source, 'answer.json');
    const stdoutText = await readTextOptional(stdoutFile);
    const stderrText = await readTextOptional(stderrFile);
    const traceText = (await readTextOptional(traceFile)) || combinedTrace(stdoutText, stderrText);

    return NextResponse.json({
      answer_text: await readTextOptional(answerFile),
      stdout_text: stdoutText,
      stderr_text: stderrText,
      trace_text: traceText,
      truncated: {
        answer_text: await isTruncated(answerFile),
        stdout_text: await isTruncated(stdoutFile),
        stderr_text: await isTruncated(stderrFile),
        trace_text: await isTruncated(traceFile),
      },
    });
  } catch (error: unknown) {
    console.error('Error loading run artifacts:', error);
    return NextResponse.json(
      { error: 'Failed to load run artifacts', details: error instanceof Error ? error.message : String(error) },
      { status: 500 }
    );
  }
}

function isSafeSegment(value: string): boolean {
  return /^[A-Za-z0-9._-]+$/.test(value);
}

function artifactPath(runDir: string, value: unknown, defaultName: string): string {
  const candidate = typeof value === 'string' && value ? value : defaultName;
  if (path.isAbsolute(candidate) && candidate.startsWith(runDir)) {
    return candidate;
  }
  return path.join(runDir, path.basename(candidate));
}

function combinedTrace(stdoutText: string, stderrText: string): string {
  const parts = [];
  if (stdoutText) parts.push(`### stdout\n${stdoutText}`);
  if (stderrText) parts.push(`### stderr\n${stderrText}`);
  return parts.join('\n\n');
}

async function readJsonOptional(filePath: string): Promise<Record<string, unknown> | null> {
  try {
    return JSON.parse(await fs.readFile(filePath, 'utf-8'));
  } catch {
    return null;
  }
}

async function readTextOptional(filePath: string): Promise<string> {
  try {
    const handle = await fs.open(filePath, 'r');
    try {
      const buffer = Buffer.alloc(MAX_ARTIFACT_BYTES);
      const { bytesRead } = await handle.read(buffer, 0, MAX_ARTIFACT_BYTES, 0);
      return buffer.subarray(0, bytesRead).toString('utf-8');
    } finally {
      await handle.close();
    }
  } catch {
    return '';
  }
}

async function isTruncated(filePath: string): Promise<boolean> {
  try {
    const stat = await fs.stat(filePath);
    return stat.size > MAX_ARTIFACT_BYTES;
  } catch {
    return false;
  }
}
