/**
 * Unit & Integration Tests for DFSS File Delete Flow, Two-Step Confirmation & Failure Rollback
 */

import { DistributedStorageClient, ApiClientError } from '../api/client.ts';
import { fileService } from '../services/fileService.ts';
import { apiService } from '../services/apiService.ts';
import {
  renderFileRow,
  renderDeleteError,
  renderFilePanel,
} from '../components/FilePanel.ts';
import type { FileInfo } from '../types/api.ts';
import type { DeleteState } from '../types/components.ts';

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

console.log('\n=== Starting DFSS File Delete & Confirmation Flow Tests ===\n');

// 1. API Client Delete Tests
console.log('Testing DistributedStorageClient.deleteFile...');

const client = new DistributedStorageClient({
  baseUrl: 'http://localhost:8000',
  fetchImpl: (async (url: string | URL | Request, init?: RequestInit) => {
    const urlStr = url.toString();
    const method = init?.method ?? 'GET';

    if (method === 'DELETE' && urlStr.includes('/files/file-valid-del')) {
      return {
        ok: true,
        status: 200,
        headers: new Headers({ 'Content-Type': 'application/json' }),
        json: async () => ({
          message: 'File deleted successfully',
          filename: 'dataset_shard_01.csv',
          file_id: 'file-valid-del',
        }),
      } as unknown as Response;
    }

    if (method === 'DELETE' && urlStr.includes('/files/file-missing')) {
      return {
        ok: false,
        status: 404,
        statusText: 'Not Found',
        headers: new Headers({ 'Content-Type': 'application/json' }),
        json: async () => ({
          detail: "File not found: 'missing.bin' does not exist in cluster.",
        }),
      } as unknown as Response;
    }

    return {
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      headers: new Headers(),
      json: async () => ({ detail: 'Node unreachable' }),
    } as unknown as Response;
  }) as unknown as typeof fetch,
});

const delResult = await client.deleteFile('file-valid-del');
assertStrictEqual(delResult.message, 'File deleted successfully', 'Returns delete success message');
assertStrictEqual(delResult.filename, 'dataset_shard_01.csv', 'Returns deleted filename');

let caughtClientError = false;
try {
  await client.deleteFile('file-missing');
} catch (err: unknown) {
  caughtClientError = true;
  assert(err instanceof ApiClientError, 'Throws ApiClientError on 404');
  if (err instanceof ApiClientError) {
    assertStrictEqual(err.status, 404, 'Captures HTTP 404 status');
    assert(
      Boolean(err.errorData?.detail?.includes('File not found')),
      'Captures explicit server error detail'
    );
  }
}
assert(caughtClientError, 'deleteFile threw expected error on 404');
console.log('  ✓ PASS: Client issues DELETE /files/{file_id}, validates response, and captures 404 error details.');

// 2. FilePanel Confirmation Step & Action Rendering
console.log('Testing FilePanel Delete Confirmation Step & Action Rendering...');

const testFile: FileInfo = {
  file_id: 'file-del-test',
  name: 'system_manifest.json',
  size: 4096,
  replicas: ['Node A', 'Node B', 'Node C'],
  status: 'REPLICATED',
  modified_at: 1724784000,
};

// Default row state: renders Download and Delete buttons
const defaultRowHtml = renderFileRow(testFile, null, null);
assert(defaultRowHtml.includes('btn-delete-file'), 'Renders delete button in row');
assert(!defaultRowHtml.includes('btn-confirm-delete'), 'Does not render confirm button by default');

// Step 1: User clicked Delete, row enters confirmation state
const confirmingState: DeleteState = {
  confirmingFileId: 'file-del-test',
  isDeleting: false,
};

const confirmingRowHtml = renderFileRow(testFile, null, confirmingState);
assert(confirmingRowHtml.includes('confirm-delete-group'), 'Renders confirm-delete-group container');
assert(confirmingRowHtml.includes('confirm-delete-prompt'), 'Displays Delete? confirmation prompt');
assert(confirmingRowHtml.includes('btn-confirm-delete'), 'Displays Confirm action button');
assert(confirmingRowHtml.includes('btn-cancel-delete'), 'Displays Cancel action button');
assert(!confirmingRowHtml.includes('btn-delete-file'), 'Hides default delete button during confirmation');
console.log('  ✓ PASS: Two-step confirmation replaces standard delete button with Confirm and Cancel controls.');

// 3. Delete Error Card Rendering
console.log('Testing Delete Error Card Rendering...');

const errorDeleteState: DeleteState = {
  confirmingFileId: null,
  isDeleting: false,
  fileId: 'file-del-test',
  error: "Quorum lost: Cannot reach majority to delete replica across nodes.",
};

const errorCardHtml = renderDeleteError(errorDeleteState);
assert(errorCardHtml.includes('delete-error-card'), 'Renders delete-error-card container');
assert(errorCardHtml.includes('role="alert"'), 'Includes ARIA role="alert"');
assert(errorCardHtml.includes('DELETE ERROR'), 'Displays DELETE ERROR badge');
assert(errorCardHtml.includes('Quorum lost'), 'Displays explicit server error message');
assert(errorCardHtml.includes('btn-dismiss-delete-error'), 'Includes Dismiss button');

const panelWithErrorHtml = renderFilePanel([testFile], 'normal', undefined, 1, 4096, '', null, null, errorDeleteState);
assert(panelWithErrorHtml.includes('delete-error-card'), 'renderFilePanel includes delete error card in status slot');
console.log('  ✓ PASS: Delete error card renders explicit error detail with dismiss control.');

// 4. FileService Delete Lifecycle: Immediate Removal & Failure Rollback
console.log('Testing FileService Immediate Removal and Failure Rollback...');

const originalDeleteFile = apiService.deleteFile.bind(apiService);
const originalGetFiles = apiService.getFiles.bind(apiService);

const fileA: FileInfo = { file_id: 'file-1', name: 'file1.bin', size: 100, replicas: ['Node A'], status: 'REPLICATED' };
const fileB: FileInfo = { file_id: 'file-2', name: 'file2.bin', size: 200, replicas: ['Node A', 'Node B'], status: 'REPLICATED' };

fileService.reset();
// Mock initial files in service
apiService.getFiles = async () => ({
  files: [fileA, fileB],
  total_files: 2,
  total_size_bytes: 300,
});
await fileService.refreshFiles();

assertStrictEqual(fileService.getResult().files.length, 2, 'Initially holds 2 files');

// Test Step 1: Setting confirming file ID
fileService.setConfirmingDelete('file-1');
assertStrictEqual(fileService.getDeleteState()?.confirmingFileId, 'file-1', 'Captures confirmingFileId');
fileService.setConfirmingDelete(null);
assertStrictEqual(fileService.getDeleteState(), null, 'Canceling confirmation resets deleteState');

// Test Step 2 (Success Flow): Optimistic immediate removal
apiService.deleteFile = async (fileId: string) => {
  // Update mock files so refreshFiles gets remaining files
  apiService.getFiles = async () => ({
    files: [fileB],
    total_files: 1,
    total_size_bytes: 200,
  });
  return {
    message: 'File deleted successfully',
    filename: 'file1.bin',
    file_id: fileId,
  };
};

const deletePromise = fileService.deleteFile('file-1');
// Immediately verify optimistic removal
assert(
  !fileService.getResult().files.some(f => f.file_id === 'file-1'),
  'File disappears from list immediately without waiting for server response'
);
assertStrictEqual(fileService.getResult().totalFiles, 1, 'Total files decremented immediately');
assertStrictEqual(fileService.getResult().totalSizeBytes, 200, 'Total size decremented immediately');
await deletePromise;

// Test Step 3 (Failure Flow): Automatic row restoration and inline error
apiService.deleteFile = async (fileId: string) => {
  throw new ApiClientError(
    'Request failed: Node B rejected replica deletion',
    500,
    `http://localhost:8000/files/${fileId}`,
    { detail: 'Node B rejected replica deletion' }
  );
};

let caughtFailure = false;
try {
  await fileService.deleteFile('file-2');
} catch {
  caughtFailure = true;
}
assert(caughtFailure, 'deleteFile re-throws error on server failure');

// Verify restoration of file row on failure
const restoredFiles = fileService.getResult().files;
assert(
  restoredFiles.some(f => f.file_id === 'file-2'),
  'Failed delete restores the file row back into the list'
);
assertStrictEqual(fileService.getResult().totalFiles, 1, 'Restores file count on failure');
assertStrictEqual(
  fileService.getDeleteState()?.error,
  'Node B rejected replica deletion',
  'Captures explicit server error detail on failure'
);

// 5. NO MAJORITY Consensus Paused Delete Guard
console.log('Testing NO MAJORITY Consensus Paused Delete Guard...');

let caughtPausedDelete = false;
try {
  await fileService.deleteFile('file-1', 'NO MAJORITY');
} catch (err: unknown) {
  caughtPausedDelete = true;
  assert(err instanceof Error && err.message.includes('Consensus is paused'), 'Error notes consensus paused');
}
assert(caughtPausedDelete, 'deleteFile during NO MAJORITY is blocked');
assert(
  Boolean(fileService.getDeleteState()?.error?.includes('Consensus is paused') && fileService.getDeleteState()?.error?.includes('quorum majority lost')),
  'Delete error specifies consensus is paused due to quorum loss'
);
fileService.dismissDeleteError();

// Cleanup
apiService.deleteFile = originalDeleteFile;
apiService.getFiles = originalGetFiles;
fileService.reset();

console.log('  ✓ PASS: FileService optimistically removes file immediately and restores row with inline error on failure.');
console.log('  ✓ PASS: FileService guards delete operations when consensus is paused under NO MAJORITY.');

console.log('\n=== All File Delete Flow Tests Passed Successfully (5/5)! ===\n');
