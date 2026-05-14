import path from 'path';
import fs from 'fs/promises';

const MAX_ARTIFACT_BYTES = 256 * 1024;

export interface RunArtifacts {
  answer_text: string;
  stdout_text: string;
  stderr_text: string;
  trace_text: string;
  truncated: {
    answer_text: boolean;
    stdout_text: boolean;
    stderr_text: boolean;
    trace_text: boolean;
  };
}

export async function buildRunArtifacts(runDir: string): Promise<RunArtifacts | null> {
  const summary = await readJsonOptional(path.join(runDir, 'run_summary.json'));
  if (!summary) return null;

  const stdoutFile = artifactPath(runDir, summary.stdout_file, 'stdout.txt');
  const stderrFile = artifactPath(runDir, summary.stderr_file, 'stderr.txt');
  const traceFile = artifactPath(runDir, summary.trace_file, 'agent_trace.txt');
  const answerFile = artifactPath(runDir, summary.answer_source, 'answer.json');

  const stdoutText = await readTextOptional(stdoutFile);
  const stderrText = await readTextOptional(stderrFile);
  const traceText = (await readTextOptional(traceFile)) || combinedTrace(stdoutText, stderrText);

  return {
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
  };
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
