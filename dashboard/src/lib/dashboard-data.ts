import path from 'path';
import fs from 'fs/promises';

type JsonObject = Record<string, unknown>;

export type DashboardRun = {
  task_id: string;
  model: string;
  run_id: string;
  run_dir: string;
  command: string;
  returncode: number | null;
  duration_seconds: number | null;
  grade: JsonObject;
  score: number | null;
  timestamp: string;
  aup_refusal: boolean;
  tags?: string[];
};

export interface RunSummaryLocation {
  taskId: string;
  runId: string;
  runDir: string;
}

export function defaultCapableBenchDir(): string {
  return path.resolve(process.cwd(), '..');
}

export async function buildDashboardData(capableBenchDir: string): Promise<JsonObject> {
  const tasksDir = path.join(capableBenchDir, 'data', 'tasks');
  const answersDir = path.join(capableBenchDir, 'data', 'answers');
  const runsDir = path.join(capableBenchDir, 'runs');

  const tasks = await listTasks(tasksDir, answersDir);
  const taskIds = new Set(tasks.map((task) => task.id));
  const runs = (await collectRuns(runsDir))
    .filter((run) => taskIds.has(run.task_id) && run.model !== 'Other')
    .map((run) => ({ ...run, tags: autoTagRun(run) }));

  const latestRuns = latestByTaskModel(runs);
  const models = [...new Set(runs.map((run) => run.model))].sort();

  return {
    tasks,
    models,
    model_summary: modelSummary(Object.values(latestRuns), models),
    latest_runs: latestRuns,
    all_runs: allByTaskModel(runs),
    task_tags: taskTags(tasks),
  };
}

export async function enumerateRunDirs(runsDir: string): Promise<RunSummaryLocation[]> {
  const summaryPaths = await findRunSummaries(runsDir);
  return summaryPaths.map((summaryPath) => {
    const runDir = path.dirname(summaryPath);
    return {
      taskId: path.basename(path.dirname(runDir)),
      runId: path.basename(runDir),
      runDir,
    };
  });
}

async function listTasks(tasksDir: string, answersDir: string): Promise<Array<JsonObject & { id: string }>> {
  const problemsPath = path.join(tasksDir, 'problems.csv');
  const problemsCsv = await readTextOptional(problemsPath);
  if (!problemsCsv) {
    return [];
  }

  const rows = parseCsv(problemsCsv);
  return Promise.all(
    rows.map(async (row) => {
      const taskDir = path.join(tasksDir, row.id);
      const prompt = await readTextOptional(path.join(taskDir, 'prompt.md'));
      const taskYamlText = await readTextOptional(path.join(taskDir, 'task.yaml'));
      const goldYamlText = await readTextOptional(path.join(answersDir, `${row.id}.yaml`));

      return {
        ...row,
        id: row.id,
        prompt,
        task_yaml: parseYamlLite(taskYamlText),
        data_files: await dataFileSummaries(taskDir),
        gold_answer: parseYamlLite(goldYamlText),
      };
    })
  );
}

async function collectRuns(runsDir: string): Promise<DashboardRun[]> {
  const summaryPaths = await findRunSummaries(runsDir);
  const runs: DashboardRun[] = [];

  for (const summaryPath of summaryPaths) {
    const summary = await readJsonOptional(summaryPath);
    if (!summary) continue;

    const runDir = path.dirname(summaryPath);
    const taskId = stringValue(summary.task_id) || path.basename(path.dirname(runDir));
    const grade = objectValue(summary.grade) || (await readJsonOptional(path.join(runDir, 'grade.json'))) || {};
    const command = stringValue(summary.command);
    const model = classifyModel(command);
    const score = scoreFromGrade(grade);
    const aupRefusal = model === 'Claude' && (await detectAupRefusal(path.join(runDir, 'stdout.txt')));

    runs.push({
      task_id: taskId,
      model,
      run_id: stringValue(summary.run_id) || path.basename(runDir),
      run_dir: runDir,
      command,
      returncode: numberValue(summary.returncode),
      duration_seconds: numberValue(summary.duration_seconds),
      grade,
      score,
      timestamp: stringValue(summary.run_id) || path.basename(runDir),
      aup_refusal: aupRefusal,
    });
  }

  return runs;
}

async function findRunSummaries(runsDir: string): Promise<string[]> {
  const paths: string[] = [];
  const taskEntries = await safeReadDir(runsDir);

  for (const taskEntry of taskEntries) {
    if (!taskEntry.isDirectory()) continue;

    const taskDir = path.join(runsDir, taskEntry.name);
    const runEntries = await safeReadDir(taskDir);
    for (const runEntry of runEntries) {
      if (!runEntry.isDirectory()) continue;

      const summaryPath = path.join(taskDir, runEntry.name, 'run_summary.json');
      if (await exists(summaryPath)) {
        paths.push(summaryPath);
      }
    }
  }

  return paths.sort();
}

function latestByTaskModel(runs: DashboardRun[]): Record<string, Record<string, DashboardRun>> {
  const latest: Record<string, Record<string, DashboardRun>> = {};
  for (const run of runs) {
    latest[run.task_id] ||= {};
    const current = latest[run.task_id][run.model];
    if (!current || String(run.timestamp) > String(current.timestamp)) {
      latest[run.task_id][run.model] = run;
    }
  }
  return latest;
}

function allByTaskModel(runs: DashboardRun[]): Record<string, Record<string, DashboardRun[]>> {
  const grouped: Record<string, Record<string, DashboardRun[]>> = {};
  for (const run of runs) {
    grouped[run.task_id] ||= {};
    grouped[run.task_id][run.model] ||= [];
    grouped[run.task_id][run.model].push(run);
  }
  for (const taskId of Object.keys(grouped)) {
    for (const model of Object.keys(grouped[taskId])) {
      grouped[taskId][model].sort((a, b) => String(b.timestamp).localeCompare(String(a.timestamp)));
    }
  }
  return grouped;
}

function taskTags(tasks: Array<JsonObject & { id: string }>): Record<string, string[]> {
  return Object.fromEntries(
    tasks.map((task) => {
      const tags: string[] = [];
      const taskType = stringValue(task.task_type);
      if (taskType) tags.push(taskType);
      return [task.id, tags];
    })
  );
}

function modelSummary(
  taskModelRuns: Record<string, DashboardRun>[],
  models: string[]
): Record<string, JsonObject> {
  const summary: Record<string, JsonObject> = {};

  for (const model of models) {
    const runs = taskModelRuns
      .filter((item) => item && item[model])
      .map((item) => item[model]);
    const scores = runs
      .map((run) => run.score)
      .filter((score): score is number => typeof score === 'number');

    let mean: number | null = null;
    let sem: number | null = null;
    if (scores.length > 0) {
      mean = scores.reduce((total, score) => total + score, 0) / scores.length;
      if (scores.length > 1) {
        // Sample variance / sqrt(n) — SEM across tasks.
        const variance =
          scores.reduce((acc, s) => acc + (s - mean!) ** 2, 0) / (scores.length - 1);
        sem = Math.sqrt(variance / scores.length);
      }
    }

    summary[model] = {
      tasks: runs.length,
      mean_score: mean !== null ? round4(mean) : null,
      sem_score: sem !== null ? round4(sem) : null,
      parsed_rate: meanBool(runs.filter((run) => run.grade).map((run) => run.grade?.parsed_answer)),
      error_rate: meanBool(runs.map((run) => run.returncode !== 0 && run.returncode != null)),
      aup_refusal_count: runs.filter((run) => run.aup_refusal).length,
    };
  }

  return summary;
}

async function dataFileSummaries(taskDir: string): Promise<JsonObject[]> {
  const entries = await safeReadDir(taskDir);
  const files: JsonObject[] = [];

  for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name))) {
    if (!entry.isFile() || entry.name === 'prompt.md' || entry.name === 'task.yaml') continue;

    const filePath = path.join(taskDir, entry.name);
    const stat = await fs.stat(filePath);
    files.push({
      name: entry.name,
      size_bytes: stat.size,
    });
  }

  return files;
}

function parseCsv(input: string): Array<Record<string, string>> {
  const rows: string[][] = [];
  let field = '';
  let row: string[] = [];
  let quoted = false;

  for (let i = 0; i < input.length; i += 1) {
    const char = input[i];
    const next = input[i + 1];

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

  const [headers = [], ...records] = rows.filter((item) => item.some(Boolean));
  return records.map((record) =>
    Object.fromEntries(headers.map((header, index) => [header, record[index] || '']))
  );
}

function parseYamlLite(input: string): JsonObject {
  const result: JsonObject = {};
  if (!input.trim()) return result;

  const lines = input.split(/\r?\n/);
  for (let i = 0; i < lines.length; i += 1) {
    const line = stripYamlComment(lines[i]);
    if (!line.trim() || line.startsWith(' ') || line.startsWith('-')) continue;

    const match = line.match(/^([^:]+):\s*(.*)$/);
    if (!match) continue;

    const key = match[1].trim();
    const rest = match[2].trim();

    if (rest === '|') {
      const block: string[] = [];
      i += 1;
      while (i < lines.length && (lines[i].startsWith(' ') || !lines[i].trim())) {
        block.push(lines[i].replace(/^  /, ''));
        i += 1;
      }
      i -= 1;
      result[key] = block.join('\n').trimEnd();
    } else if (rest) {
      result[key] = parseScalar(rest);
    } else {
      const values: unknown[] = [];
      const objectValue: JsonObject = {};
      let sawArray = false;
      let sawObject = false;

      i += 1;
      while (i < lines.length && (lines[i].startsWith(' ') || !lines[i].trim())) {
        const child = stripYamlComment(lines[i]);
        const trimmed = child.trim();
        if (!trimmed) {
          i += 1;
          continue;
        }
        if (trimmed.startsWith('- ')) {
          sawArray = true;
          values.push(parseScalar(trimmed.slice(2).trim()));
        } else {
          const childMatch = trimmed.match(/^([^:]+):\s*(.*)$/);
          if (childMatch) {
            sawObject = true;
            objectValue[childMatch[1].trim()] = parseScalar(childMatch[2].trim());
          }
        }
        i += 1;
      }
      i -= 1;
      result[key] = sawArray && !sawObject ? values : objectValue;
    }
  }

  result.__raw = input;
  return result;
}

function stripYamlComment(line: string): string {
  let quoted = false;
  let quote = '';
  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    if ((char === '"' || char === "'") && (!quoted || quote === char)) {
      quoted = !quoted;
      quote = quoted ? char : '';
    }
    if (!quoted && char === '#' && (i === 0 || /\s/.test(line[i - 1]))) {
      return line.slice(0, i).trimEnd();
    }
  }
  return line;
}

function parseScalar(value: string): unknown {
  if (value === '') return '';
  if (value === 'null' || value === '~') return null;
  if (value === 'true') return true;
  if (value === 'false') return false;
  if (/^-?\d+(\.\d+)?$/.test(value)) return Number(value);
  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    return value.slice(1, -1);
  }
  return value;
}

function classifyModel(command: string): string {
  const lower = command.toLowerCase();
  if (lower.includes('codex')) return 'Codex';
  if (lower.includes('claude')) return 'Claude';
  if (lower.includes('modal')) return 'Modal';
  return 'Other';
}

function scoreFromGrade(grade: JsonObject | null): number | null {
  if (!grade || typeof grade !== 'object') return null;
  const rawScore = grade.score ?? grade.precision_at_k;
  const score = Number(rawScore);
  return Number.isFinite(score) ? score : null;
}

function stringValue(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

function numberValue(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function objectValue(value: unknown): JsonObject | null {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as JsonObject) : null;
}

function meanBool(values: unknown[]): number | null {
  if (!values.length) return null;
  return round4(values.filter(Boolean).length / values.length);
}

function round4(value: number): number {
  return Math.round(value * 10000) / 10000;
}

function autoTagRun(run: DashboardRun): string[] {
  const tags: string[] = [];
  if (run.aup_refusal) tags.push('aup_refusal');
  if (run.grade.parsed_answer === false) tags.push('format_error');
  if (run.returncode && run.returncode !== 0) tags.push('execution_error');
  if (run.score !== null && run.score !== undefined) {
    if (run.score < 0.3) tags.push('low_score');
  }
  return tags;
}

async function detectAupRefusal(stdoutPath: string): Promise<boolean> {
  // `"stop_reason":"refusal"` is the authoritative signal in claude stream-json
  // when the model refuses on Usage Policy grounds. Refusals terminate early so
  // a 256KB head read is enough to cover every refusal we've seen in this repo.
  const text = await readTextOptional(stdoutPath, 256 * 1024);
  if (!text) return false;
  return text.includes('"stop_reason":"refusal"');
}

async function readTextOptional(filePath: string, maxBytes?: number): Promise<string> {
  try {
    if (!maxBytes) {
      return await fs.readFile(filePath, 'utf-8');
    }
    const handle = await fs.open(filePath, 'r');
    try {
      const buffer = Buffer.alloc(maxBytes);
      const { bytesRead } = await handle.read(buffer, 0, maxBytes, 0);
      return buffer.subarray(0, bytesRead).toString('utf-8');
    } finally {
      await handle.close();
    }
  } catch {
    return '';
  }
}

async function readJsonOptional(filePath: string): Promise<JsonObject | null> {
  try {
    return JSON.parse(await fs.readFile(filePath, 'utf-8'));
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

async function exists(filePath: string): Promise<boolean> {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}
