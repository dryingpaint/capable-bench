/**
 * Pre-build script: snapshots dynamic dashboard data into static assets
 * under dashboard/public/ so the site can be served from Cloudflare Pages
 * without runtime filesystem access.
 *
 * Produces:
 *   public/dashboard.json
 *   public/run-artifacts/<taskId>/<runId>.json
 *   public/finding-files/<findingId>/<...path>   (non-README files only)
 */

import path from 'path';
import fs from 'fs/promises';
import { fileURLToPath } from 'url';
import {
  buildDashboardData,
  enumerateRunDirs,
  defaultCapableBenchDir,
} from '../src/lib/dashboard-data';
import { buildRunArtifacts } from '../src/lib/run-artifacts';

const SAFE_ID = /^[A-Za-z0-9._-]+$/;

async function main() {
  const dashboardRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
  const capableBenchDir = defaultCapableBenchDir();
  const publicDir = path.join(dashboardRoot, 'public');

  const dashboardOut = path.join(publicDir, 'dashboard.json');
  const runArtifactsOut = path.join(publicDir, 'run-artifacts');
  const findingFilesOut = path.join(publicDir, 'finding-files');

  await rmrf(runArtifactsOut);
  await rmrf(findingFilesOut);
  await fs.mkdir(publicDir, { recursive: true });

  console.log('[bake] capablebench root:', capableBenchDir);

  console.log('[bake] writing dashboard.json...');
  const dashboardData = await buildDashboardData(capableBenchDir);
  await fs.writeFile(dashboardOut, JSON.stringify(dashboardData));
  console.log('[bake]   wrote', dashboardOut);

  console.log('[bake] baking run artifacts...');
  const runs = await enumerateRunDirs(path.join(capableBenchDir, 'runs'));
  let baked = 0;
  for (const { taskId, runId, runDir } of runs) {
    if (!SAFE_ID.test(taskId) || !SAFE_ID.test(runId)) continue;
    const artifacts = await buildRunArtifacts(runDir);
    if (!artifacts) continue;
    const outDir = path.join(runArtifactsOut, taskId);
    await fs.mkdir(outDir, { recursive: true });
    await fs.writeFile(path.join(outDir, `${runId}.json`), JSON.stringify(artifacts));
    baked += 1;
  }
  console.log('[bake]   baked', baked, 'run-artifact JSONs');

  console.log('[bake] copying finding files...');
  const findingsRoot = path.join(capableBenchDir, 'docs', 'findings');
  const findingEntries = await safeReadDir(findingsRoot);
  let copiedFiles = 0;
  for (const entry of findingEntries) {
    if (!entry.isDirectory() || !SAFE_ID.test(entry.name)) continue;
    const findingSrc = path.join(findingsRoot, entry.name);
    const findingDst = path.join(findingFilesOut, entry.name);
    copiedFiles += await copyFindingFiles(findingSrc, findingDst);
  }
  console.log('[bake]   copied', copiedFiles, 'finding artifact files');

  console.log('[bake] done');
}

async function copyFindingFiles(srcDir: string, dstDir: string): Promise<number> {
  let count = 0;
  const entries = await safeReadDir(srcDir);
  for (const entry of entries) {
    const srcPath = path.join(srcDir, entry.name);
    const dstPath = path.join(dstDir, entry.name);
    if (entry.isDirectory()) {
      count += await copyFindingFiles(srcPath, dstPath);
      continue;
    }
    if (!entry.isFile()) continue;
    // The README is rendered into the page itself — don't ship it as an artifact too.
    if (entry.name === 'README.md' || entry.name === 'readme.md') continue;
    await fs.mkdir(path.dirname(dstPath), { recursive: true });
    await fs.copyFile(srcPath, dstPath);
    count += 1;
  }
  return count;
}

async function safeReadDir(dirPath: string) {
  try {
    return await fs.readdir(dirPath, { withFileTypes: true });
  } catch {
    return [];
  }
}

async function rmrf(targetPath: string) {
  try {
    await fs.rm(targetPath, { recursive: true, force: true });
  } catch {
    /* swallow */
  }
}

main().catch((error) => {
  console.error('[bake] failed:', error);
  process.exit(1);
});
