import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import fs from 'fs/promises';

const execAsync = promisify(exec);

export async function GET() {
  try {
    const capableBenchDir = path.resolve(process.cwd(), '..');

    // Get all findings directories and files
    const { stdout } = await execAsync(`cd "${capableBenchDir}" && find docs/findings -name "*.md" | sort`);

    const findingFiles = stdout.trim().split('\n').filter(Boolean);

    const findings = [];

    for (const filePath of findingFiles) {
      if (filePath.includes('README.md')) continue; // Skip README files for now

      try {
        const fullPath = path.join(capableBenchDir, filePath);
        const content = await fs.readFile(fullPath, 'utf-8');
        const fileName = path.basename(filePath, '.md');
        const dirName = path.basename(path.dirname(filePath));

        // Parse title from content if available
        const lines = content.split('\n');
        let title = fileName;
        const titleLine = lines.find(line => line.startsWith('# '));
        if (titleLine) {
          title = titleLine.replace('# ', '');
        }

        findings.push({
          id: `${dirName}/${fileName}`,
          title,
          path: filePath,
          directory: dirName,
          filename: fileName,
          content: content.substring(0, 2000) + (content.length > 2000 ? '...' : ''), // Truncate for list view
          fullContent: content,
          lastModified: (await fs.stat(fullPath)).mtime,
        });
      } catch (error) {
        console.error(`Error reading finding ${filePath}:`, error);
      }
    }

    // Sort by last modified date (newest first)
    findings.sort((a, b) => new Date(b.lastModified).getTime() - new Date(a.lastModified).getTime());

    return NextResponse.json({
      findings,
      total: findings.length
    });

  } catch (error: unknown) {
    console.error('Error loading findings:', error);
    return NextResponse.json(
      {
        error: 'Failed to load findings',
        details: error instanceof Error ? error.message : String(error)
      },
      { status: 500 }
    );
  }
}
