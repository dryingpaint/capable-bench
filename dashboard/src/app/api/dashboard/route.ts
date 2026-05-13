import { NextRequest, NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import fs from 'fs/promises';
import crypto from 'crypto';

const execAsync = promisify(exec);

// Cache state
let cache: {
  data: any;
  hash: string;
  timestamp: number;
} | null = null;

// Cache for 30 seconds minimum to avoid thrashing
const CACHE_TTL = 30 * 1000;

export async function GET(request: NextRequest) {
  try {
    const capableBenchDir = path.resolve(process.cwd(), '..');
    const runsDir = path.join(capableBenchDir, 'runs');

    // Check if we can use cached data
    const currentHash = await getRunsDirectoryHash(runsDir);
    const now = Date.now();

    if (cache &&
        cache.hash === currentHash &&
        (now - cache.timestamp) < CACHE_TTL) {
      console.log('Using cached dashboard data');
      return NextResponse.json(cache.data);
    }

    console.log('Regenerating dashboard data...');

    // Use optimized viewer with caching hints
    const { stdout, stderr } = await execAsync(`cd "${capableBenchDir}" && uv run python -c "
import json
import sys
import os
from pathlib import Path

# Debug info
print('Working directory:', os.getcwd(), file=sys.stderr)
print('Python path:', sys.path[:3], file=sys.stderr)

# Add the current directory to Python path so capablebench module is found
sys.path.insert(0, '.')

try:
    from capablebench.viewer import _collect_runs, list_tasks, _latest_by_task_model, _model_summary, _read_yaml_optional, _read_text, _data_file_summaries, _read_json_optional
    from capablebench.io import read_yaml

    # Use the same paths as the existing setup
    tasks_dir = Path('data/tasks')
    answers_dir = Path('data/answers')
    runs_dir = Path('runs')

    # Build the data directly (based on build_viewer but return JSON instead of HTML)
    all_tasks = list_tasks(tasks_dir)

    # Filter out tasks with poor validators (expert_rubric uses keyword matching)
    tasks = [task for task in all_tasks if task.get('label_status') != 'expert_rubric']

    task_ids = {task['id'] for task in tasks}
    runs = [run for run in _collect_runs(runs_dir, answers_dir) if run['task_id'] in task_ids and run.get('model') != 'Other']
    latest_by_task_model = _latest_by_task_model(runs)
    models = sorted({run['model'] for run in runs if run.get('model') != 'Other'})

    task_rows = []
    for task in tasks:
        task_id = task['id']
        task_dir = tasks_dir / task_id
        task_rows.append({
            **task,
            'prompt': _read_text(task_dir / 'prompt.md'),
            'task_yaml': _read_yaml_optional(task_dir / 'task.yaml'),
            'data_files': _data_file_summaries(task_dir),
            'latest_runs': latest_by_task_model.get(task_id, {}),
            'gold_answer': _read_yaml_optional(answers_dir / f'{task_id}.yaml'),
        })

    model_summary = _model_summary(list(latest_by_task_model.values()), models)
    calibration = _read_json_optional(runs_dir / 'calibration_summary.json')

    # Build the payload
    data = {
        'tasks': task_rows,
        'models': models,
        'model_summary': model_summary,
        'latest_runs': latest_by_task_model,  # Add this for frontend compatibility
        'runs': runs,  # include_all_runs=True
        'calibration': calibration,
    }

    # Optimize: limit trace text size to reduce memory usage
    for run in data.get('runs', []):
        for key in ['stdout_text', 'stderr_text', 'trace_text']:
            if key in run and run[key] and len(run[key]) > 10000:
                run[key] = run[key][:10000] + '... [truncated]'

    print(json.dumps(data, default=str))
except Exception as e:
    print('Error:', str(e), file=sys.stderr)
    raise
"`, { maxBuffer: 50 * 1024 * 1024 }); // 50MB buffer

    const data = JSON.parse(stdout);

    // Transform the data to add our tagging system
    const enhancedData = {
      ...data,
      runs: data.runs?.map((run: any) => ({
        ...run,
        tags: autoTagRun(run)
      })) || []
    };

    // Update cache
    cache = {
      data: enhancedData,
      hash: currentHash,
      timestamp: now
    };

    return NextResponse.json(enhancedData);
  } catch (error: any) {
    console.error('Error generating dashboard data:', error);
    console.error('Stdout:', error.stdout);
    console.error('Stderr:', error.stderr);
    return NextResponse.json(
      {
        error: 'Failed to generate dashboard data',
        details: error.message,
        stderr: error.stderr?.substring(0, 500)
      },
      { status: 500 }
    );
  }
}

// Generate a hash of the runs directory to detect changes
async function getRunsDirectoryHash(runsDir: string): Promise<string> {
  try {
    const hash = crypto.createHash('md5');

    // Hash based on directory structure and key file timestamps
    const entries = await fs.readdir(runsDir, { withFileTypes: true });

    // Sort for consistent hashing
    const sortedEntries = entries.sort((a, b) => a.name.localeCompare(b.name));

    for (const entry of sortedEntries) {
      if (entry.isDirectory()) {
        const dirPath = path.join(runsDir, entry.name);
        hash.update(entry.name);

        try {
          // Check modification time of the directory itself
          const stats = await fs.stat(dirPath);
          hash.update(stats.mtime.toISOString());

          // Hash key files if they exist
          const keyFiles = ['run_summary.json', 'grade.json'];
          for (const file of keyFiles) {
            try {
              const filePath = path.join(dirPath, file);
              const fileStat = await fs.stat(filePath);
              hash.update(file + fileStat.mtime.toISOString());
            } catch {
              // File doesn't exist, skip
            }
          }
        } catch {
          // Directory access error, skip
        }
      } else if (entry.name.endsWith('.json')) {
        // Top-level JSON files (like latest_suite_summary.json)
        const filePath = path.join(runsDir, entry.name);
        try {
          const stats = await fs.stat(filePath);
          hash.update(entry.name + stats.mtime.toISOString());
        } catch {
          // File access error, skip
        }
      }
    }

    return hash.digest('hex');
  } catch (error) {
    // If we can't hash, return a timestamp to force refresh
    return Date.now().toString();
  }
}

function autoTagRun(run: any): string[] {
  const tags: string[] = [];

  // Saturation detection
  if (run.score >= 0.9 && run.task?.difficulty === 'hard') {
    tags.push('saturation');
  }

  // Format compliance issues
  if (run.grade && !run.grade.parsed_answer) {
    tags.push('format_error');
  }

  // Performance issues
  if (run.returncode && run.returncode !== 0) {
    tags.push('execution_error');
  }

  // Score-based classifications
  if (run.score !== null && run.score !== undefined) {
    if (run.score < 0.3) {
      tags.push('low_score');
    } else if (run.score > 0.9) {
      tags.push('high_score');
    }
  }

  return tags;
}