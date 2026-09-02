/**
 * Unit & Integration Tests for DFSS File Download Flow & Replica Error Handling
 */

import { DistributedStorageClient, ApiClientError } from '../api/client.ts';
import { fileService } from '../services/fileService.ts';
import { apiService } from '../services/apiService.ts';
import {
  renderFileRow,
  renderDownloadError,
  renderFilePanel,
} from '../components/FilePanel.ts';
import type { FileInfo } from '../types/api.ts';
import type { DownloadState } from '../types/components.ts';

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

console.log('\n=== Starting DFSS File Download & Replica Error Handling Tests ===\n');

// 1. API Client Download Tests
console.log('Testing DistributedStorageClient.downloadFile...');

const mockBlobContent = new Uint8Array([1, 2, 3, 4, 5]);

const client = new DistributedStorageClient({
  baseUrl: 'http://localhost:8000',
  fetchImpl: (async (url: string | URL | Request) => {
    const urlStr = url.toString();
    if (urlStr.includes('/files/file-valid-123')) {
      return {
        ok: true,
        status: 200,
        headers: new Headers({
          'Content-Disposition': 'attachment; filename="distributed_archive.tar.gz"',
          'Content-Type': 'application/octet-stream',
        }),
        blob: async () => new Blob([mockBlobContent]),
      } as unknown as Response;
    }

    if (urlStr.includes('/files/file-missing-replica')) {
      return {
        ok: false,
        status: 404,
        statusText: 'Not Found',
        headers: new Headers({ 'Content-Type': 'application/json' }),
        json: async () => ({
          detail: "File replica unavailable: No active storage node holds a valid replica for 'file-missing-replica'.",
        }),
      } as unknown as Response;
    }

    return {
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      headers: new Headers(),
      json: async () => ({ detail: 'Storage failure' }),
    } as unknown as Response;
  }) as unknown as typeof fetch,
});

const downloadResult = await client.downloadFile('file-valid-123');
assertStrictEqual(downloadResult.filename, 'distributed_archive.tar.gz', 'Extracts filename from Content-Disposition');
assert(downloadResult.blob instanceof Blob, 'Returns binary Blob');

let caughtClientError = false;
try {
  await client.downloadFile('file-missing-replica');
} catch (err: unknown) {
  caughtClientError = true;
  assert(err instanceof ApiClientError, 'Throws ApiClientError on 404');
  if (err instanceof ApiClientError) {
    assertStrictEqual(err.status, 404, 'Captures HTTP 404 status');
    assert(
      Boolean(err.errorData?.detail?.includes('File replica unavailable')),
      'Captures explicit server error detail'
    );
  }
}
assert(caughtClientError, 'downloadFile threw expected error on 404');
console.log('  ✓ PASS: Client downloads blob, extracts Content-Disposition filename, and handles replica 404s.');

// 2. FilePanel Download Action & Row Rendering
console.log('Testing FilePanel Download Button & Row Rendering...');

const testFile: FileInfo = {
  file_id: 'file-abcdef12',
  name: 'dataset_shard_01.csv',
  size: 20971520, // 20 MB
  replicas: ['Node A', 'Node B'],
  status: 'REPLICATED',
  modified_at: 1724784000,
};

const defaultRowHtml = renderFileRow(testFile);
assert(defaultRowHtml.includes('btn-download-file'), 'Renders download button in row');
assert(defaultRowHtml.includes('data-file-id="file-abcdef12"'), 'Row button includes data-file-id attribute');
assert(defaultRowHtml.includes('data-filename="dataset_shard_01.csv"'), 'Row button includes data-filename attribute');
assert(defaultRowHtml.includes('Download'), 'Default button text is Download');
assert(!defaultRowHtml.includes('disabled'), 'Default button is enabled');

const activeDownloadState: DownloadState = {
  isDownloading: true,
  fileId: 'file-abcdef12',
  filename: 'dataset_shard_01.csv',
  error: null,
};

const activeRowHtml = renderFileRow(testFile, activeDownloadState);
assert(activeRowHtml.includes('disabled'), 'Button is disabled while downloading');
assert(activeRowHtml.includes('Downloading...'), 'Button displays Downloading... label');
console.log('  ✓ PASS: renderFileRow includes download action button and reflects active download state.');

// 3. Download Error Card Rendering
console.log('Testing Download Error Card Rendering...');

const errorDownloadState: DownloadState = {
  isDownloading: false,
  fileId: 'file-dead-replica',
  filename: 'missing_replica.bin',
  error: "File replica unavailable: No active storage node holds a valid replica for 'missing_replica.bin'.",
};

const errorCardHtml = renderDownloadError(errorDownloadState);
assert(errorCardHtml.includes('download-error-card'), 'Renders download-error-card container');
assert(errorCardHtml.includes('role="alert"'), 'Includes ARIA role="alert"');
assert(errorCardHtml.includes('REPLICA ERROR'), 'Displays REPLICA ERROR badge');
assert(errorCardHtml.includes('No active storage node holds a valid replica'), 'Displays explicit server detail');
assert(errorCardHtml.includes('btn-dismiss-download-error'), 'Includes Dismiss error button');

const emptyErrorHtml = renderDownloadError(null);
assertStrictEqual(emptyErrorHtml, '', 'Returns empty string when error is null');

const panelWithErrorHtml = renderFilePanel([testFile], 'normal', undefined, 1, 20971520, '', null, errorDownloadState);
assert(panelWithErrorHtml.includes('download-error-card'), 'renderFilePanel includes download error banner in status slot');
assert(panelWithErrorHtml.includes('<th>Action</th>'), 'Table header includes Action column');
console.log('  ✓ PASS: Download error card renders explicit replica failure message with dismiss action.');

// 4. FileService Download Lifecycle & Error Management
console.log('Testing FileService Download Lifecycle & Error State...');

const originalDownloadFile = apiService.downloadFile.bind(apiService);

if (typeof globalThis.URL.createObjectURL === 'undefined') {
  globalThis.URL.createObjectURL = () => 'blob:http://localhost:8000/mock-uuid';
  globalThis.URL.revokeObjectURL = () => {};
}

apiService.downloadFile = async (fileId: string) => {
  if (fileId === 'file-ok') {
    return {
      blob: new Blob([mockBlobContent]),
      filename: 'downloaded_asset.png',
    };
  }
  const err = new ApiClientError(
    "Request failed: File replica unavailable: No active storage node holds a valid replica for 'file-broken'.",
    404,
    `http://localhost:8000/files/${fileId}`,
    { detail: "File replica unavailable: No active storage node holds a valid replica for 'file-broken'." }
  );
  throw err;
};

fileService.reset();
let receivedDownloadStates: (DownloadState | null)[] = [];
const unsubscribe = fileService.subscribe((res) => {
  receivedDownloadStates.push(res.downloadState);
});

// Success flow
await fileService.downloadFile('file-ok', 'downloaded_asset.png');
assertStrictEqual(fileService.getDownloadState(), null, 'Download state cleared on successful completion');

// Error flow
let caughtServiceError = false;
try {
  await fileService.downloadFile('file-broken', 'corrupt_asset.png');
} catch {
  caughtServiceError = true;
}
assert(caughtServiceError, 'fileService.downloadFile re-throws error');
const failedState = fileService.getDownloadState();
assert(failedState !== null, 'Download state captures failure');
assertStrictEqual(failedState?.isDownloading, false, 'isDownloading is false on failure');
assert(
  Boolean(failedState?.error?.includes('File replica unavailable')),
  'Records explicit replica unavailable error'
);

// Dismiss error
fileService.dismissDownloadError();
assertStrictEqual(fileService.getDownloadState(), null, 'dismissDownloadError clears download error banner');

unsubscribe();
apiService.downloadFile = originalDownloadFile;
fileService.reset();

console.log('  ✓ PASS: FileService manages download lifecycle, surfaces explicit replica errors, and supports dismiss.');

console.log('\n=== All File Download & Replica Error Handling Tests Passed Successfully (4/4)! ===\n');
