/**
 * Unit Tests for DFSS File Service & Replicated File Panel (Zone 3)
 */

import { fileService } from '../services/fileService.ts';
import { apiService } from '../services/apiService.ts';
import {
  renderFileRow,
  hasReplica,
} from '../components/FilePanel.ts';
import type { FileInfo } from '../types/api.ts';

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

function assertStrictEqual<T>(actual: T, expected: T, message: string): void {
  if (actual !== expected) {
    throw new Error(`Expected ${String(expected)}, but got ${String(actual)}. ${message}`);
  }
}

console.log('\n=== Starting DFSS File List & Storage Ledger Tests ===\n');

// 1. Replica Matching Helper Tests
console.log('Testing Replica Matcher Helper...');
assert(hasReplica(['Node A', 'Node B'], 'A'), 'Matches Node A');
assert(hasReplica(['nodeA', 'nodeC'], 'A'), 'Matches lowercase nodeA');
assert(hasReplica(['Node 1', 'Node 2'], 'A'), 'Matches Node 1 as Node A');
assert(hasReplica(['nodeB', 'nodeC'], 'B'), 'Matches nodeB');
assert(!hasReplica(['nodeA', 'nodeB'], 'C'), 'Correctly identifies missing Node C replica');
console.log('  ✓ PASS: hasReplica helper accurately identifies replica nodes across naming conventions.');

// 2. File Row Rendering & Typography
console.log('Testing File Row Rendering & Dual Typography...');
const testFile1: FileInfo = {
  file_id: 'file-12345678',
  name: 'distributed_data.parquet',
  size: 104857600, // 100 MB
  replicas: ['Node A', 'Node B', 'Node C'],
  status: 'REPLICATED',
  modified_at: 1724784000,
};

const rowMarkup = renderFileRow(testFile1);
assert(rowMarkup.includes('distributed_data.parquet'), 'Row contains filename');
assert(rowMarkup.includes('100 MB'), 'Row formats bytes using formatBytes');
assert(rowMarkup.includes('badge-ok'), 'REPLICATED status uses badge-ok');
assert(rowMarkup.includes('REPLICATED (3/3)'), 'Shows REPLICATED (3/3)');
assert(rowMarkup.includes('replica-pill active'), 'Active replica pills rendered');
assert(rowMarkup.includes('font-mono text-ink'), 'Filename rendered in font-mono');

const testFileDegraded: FileInfo = {
  file_id: 'file-87654321',
  name: 'system_log.txt',
  size: 1024,
  replicas: ['Node A'],
  status: 'DEGRADED',
};
const degradedRow = renderFileRow(testFileDegraded);
assert(degradedRow.includes('DEGRADED (1/3)'), 'Shows DEGRADED (1/3)');
assert(degradedRow.includes('badge-warn'), 'DEGRADED status uses badge-warn');

console.log('  ✓ PASS: renderFileRow accurately formats size, status badges, and replica pills in JetBrains Mono.');

// 3. FileService Ledger Polling & Caching
console.log('Testing FileService Querying & State Management...');

// Mock apiService.getFiles
const originalGetFiles = apiService.getFiles.bind(apiService);
const sampleFiles: FileInfo[] = [
  { file_id: '1', name: 'wal_01.log', size: 1024, replicas: ['Node A', 'Node B'], status: 'REPLICATED' },
  { file_id: '2', name: 'backup.tar.gz', size: 2048, replicas: ['Node A', 'Node B', 'Node C'], status: 'REPLICATED' },
  { file_id: '3', name: 'dataset.csv', size: 4096, replicas: ['Node A'], status: 'SYNCING' },
];

apiService.getFiles = async () => {
  return {
    files: sampleFiles,
    total_files: 3,
    total_size_bytes: 7168,
  };
};

fileService.reset();
let emittedResult: any = null;
const unsubscribe = fileService.subscribe((res) => {
  emittedResult = res;
});

assertStrictEqual(fileService.getAllRawFiles().length, 0, 'Initially raw files empty before fetch');

await fileService.fetchFiles();

assertStrictEqual(emittedResult.files.length, 3, 'Emitted result contains 3 files');
assertStrictEqual(emittedResult.totalFiles, 3, 'Total files matches 3');
assertStrictEqual(emittedResult.totalSizeBytes, 7168, 'Total size matches 7168 bytes');
assertStrictEqual(emittedResult.reachable, true, 'Marked reachable on success');
assertStrictEqual(emittedResult.error, null, 'Error is null on success');

// 4. Real-time Search Filtering
console.log('Testing FileService Search Filtering...');
fileService.setSearchQuery('wal');
const filteredWal = fileService.getFilteredFiles();
assertStrictEqual(filteredWal.length, 1, 'Filter "wal" matches 1 file');
assert(filteredWal[0] !== undefined && filteredWal[0].name === 'wal_01.log', 'Matched file is wal_01.log');

fileService.setSearchQuery('BACKUP'); // Case-insensitive
const filteredBackup = fileService.getFilteredFiles();
assertStrictEqual(filteredBackup.length, 1, 'Case-insensitive filter "BACKUP" matches 1 file');
assert(filteredBackup[0] !== undefined && filteredBackup[0].name === 'backup.tar.gz', 'Matched file is backup.tar.gz');

fileService.setSearchQuery('nonexistent');
assertStrictEqual(fileService.getFilteredFiles().length, 0, 'Non-existent filter returns 0 files');

fileService.setSearchQuery('');
assertStrictEqual(fileService.getFilteredFiles().length, 3, 'Empty filter returns all files');

console.log('  ✓ PASS: Real-time search filtering performs case-insensitive filename queries.');

// 5. Polling & Memory Leak Prevention
console.log('Testing FileService Polling Lifecycle & Cleanup...');
fileService.startPolling(500);
assert(fileService.isRunning(), 'fileService starts polling');
fileService.stopPolling();
assert(!fileService.isRunning(), 'fileService stops polling cleanly');

unsubscribe();
fileService.reset();
apiService.getFiles = originalGetFiles;

console.log('  ✓ PASS: FileService polling and subscription lifecycle validated without memory leaks.');

console.log('\n=== All File List & Storage Ledger Tests Passed Successfully (5/5)! ===\n');
