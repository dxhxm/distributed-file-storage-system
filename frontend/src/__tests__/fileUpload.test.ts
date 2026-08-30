/**
 * Unit & Integration Tests for DFSS File Upload, Progress Tracking, and Dropzone
 */

import { fileService } from '../services/fileService.ts';
import { apiService } from '../services/apiService.ts';
import {
  renderFilePanel,
  renderUploadProgress,
  renderFilePanelEmpty,
} from '../components/FilePanel.ts';
import type { UploadState } from '../types/components.ts';
import type { FilesResponse } from '../types/api.ts';

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

console.log('\n=== Starting DFSS File Upload & Drag-and-Drop Tests ===\n');

// 1. Upload Progress Card Rendering & Monospace Telemetry
console.log('Testing Upload Progress Card Rendering & Monospace Telemetry...');
const activeUploadState: UploadState = {
  isUploading: true,
  filename: 'distributed_database_dump.sql.gz',
  percent: 65,
  loadedBytes: 68157440, // ~65 MB
  totalBytes: 104857600, // 100 MB
  error: null,
};

const progressMarkup = renderUploadProgress(activeUploadState);
assert(progressMarkup.includes('upload-progress-card'), 'Renders upload-progress-card element');
assert(progressMarkup.includes('distributed_database_dump.sql.gz'), 'Displays exact filename');
assert(progressMarkup.includes('65%'), 'Displays percentage in monospace');
assert(progressMarkup.includes('width: 65%;'), 'Sets progress bar width style to 65%');
assert(progressMarkup.includes('65 MB / 100 MB') || progressMarkup.includes('65.0 MB / 100 MB'), 'Formats byte transfer progress');
assert(progressMarkup.includes('badge-info'), 'Uses badge-info for uploading status badge');
console.log('  ✓ PASS: Upload progress card accurately renders file, percentage, and byte counts.');

// 2. Inline Error Banner Rendering & Action Buttons
console.log('Testing Inline Error Card & Action Buttons...');
const failedUploadState: UploadState = {
  isUploading: false,
  filename: 'kernel_image.iso',
  percent: 0,
  loadedBytes: 0,
  totalBytes: 524288000,
  error: 'Upload failed: Coordinator node HTTP 503 Quorum Lost',
};

const errorMarkup = renderUploadProgress(failedUploadState);
assert(errorMarkup.includes('upload-error-card'), 'Renders upload-error-card element');
assert(errorMarkup.includes('role="alert"'), 'Includes ARIA role="alert" for assistive tech');
assert(errorMarkup.includes('badge-down'), 'Uses badge-down for upload failure');
assert(errorMarkup.includes('Coordinator node HTTP 503 Quorum Lost'), 'Displays clear inline error text');
assert(errorMarkup.includes('btn-retry-upload'), 'Includes Retry action button');
assert(errorMarkup.includes('btn-dismiss-upload-error'), 'Includes Dismiss action button');
console.log('  ✓ PASS: Upload error banner displays clear inline message with retry and dismiss controls.');

// 3. Dropzone & File Input DOM Markup
console.log('Testing Dropzone Overlay & Hidden File Input...');
const panelWithDropzone = renderFilePanel([], 'normal');
assert(panelWithDropzone.includes('file-dropzone'), 'Panel includes file-dropzone wrapper');
assert(panelWithDropzone.includes('file-drop-overlay'), 'Panel includes file-drop-overlay');
assert(panelWithDropzone.includes('DROP TO REPLICATE'), 'Overlay contains drop action badge');
assert(panelWithDropzone.includes('file-upload-input'), 'Panel includes hidden file-upload-input');
assert(panelWithDropzone.includes('btn-upload-file'), 'Panel includes Upload File trigger button');

const emptyPanelWithDropzone = renderFilePanelEmpty();
assert(emptyPanelWithDropzone.includes('file-dropzone'), 'Empty state includes file-dropzone');
assert(emptyPanelWithDropzone.includes('file-upload-input'), 'Empty state includes file-upload-input');
console.log('  ✓ PASS: File panel contains dropzone overlay and accessible file upload trigger inputs.');

// 4. FileService Upload Lifecycle, Progress Notifications, & Auto Refresh
console.log('Testing FileService Upload Lifecycle & Progress Flow...');

const originalUploadFile = apiService.uploadFile.bind(apiService);
const originalGetFiles = apiService.getFiles.bind(apiService);

const mockBlob = { size: 1048576, name: 'telemetry_log.bin' } as unknown as File;
const progressEvents: number[] = [];

apiService.uploadFile = async (_file, _name, options) => {
  if (options?.onProgress) {
    options.onProgress(25, 262144, 1048576);
    options.onProgress(75, 786432, 1048576);
    options.onProgress(100, 1048576, 1048576);
  }
  return { message: 'File uploaded & replicated', filename: 'telemetry_log.bin' };
};

let getFilesCalled = false;
apiService.getFiles = async (): Promise<FilesResponse> => {
  getFilesCalled = true;
  return {
    files: [
      {
        file_id: 'file-telemetry-01',
        name: 'telemetry_log.bin',
        size: 1048576,
        replicas: ['Node A', 'Node B', 'Node C'],
        status: 'REPLICATED',
      },
    ],
    total_files: 1,
    total_size_bytes: 1048576,
  };
};

fileService.reset();
const unsubscribe = fileService.subscribe((res) => {
  if (res.uploadState?.isUploading) {
    progressEvents.push(res.uploadState.percent);
  }
});

const uploadResult = await fileService.uploadFile(mockBlob, 'telemetry_log.bin');
assertStrictEqual(uploadResult.filename, 'telemetry_log.bin', 'Upload returns filename');
assert(getFilesCalled, 'Refreshes files ledger on successful upload');
assert(progressEvents.includes(25) && progressEvents.includes(75), 'Dispatched intermediate progress updates');
assertStrictEqual(fileService.getAllRawFiles().length, 1, 'File appended to ledger without page reload');

unsubscribe();

// 5. Upload Error Handling & Dismissal
console.log('Testing Upload Error Handling & Dismissal...');

apiService.uploadFile = async () => {
  throw new Error('Connection refused by storage cluster');
};

let caughtError = false;
try {
  await fileService.uploadFile(mockBlob, 'failing_file.bin');
} catch (err: unknown) {
  caughtError = true;
  assert(err instanceof Error, 'Catches upload error');
}

assert(caughtError, 'uploadFile throws error to caller');
const errorState = fileService.getUploadState();
assert(errorState !== null, 'Upload state retained for error display');
assertStrictEqual(errorState?.isUploading, false, 'isUploading is false');
assert(Boolean(errorState?.error?.includes('Connection refused')), 'Error message recorded');

fileService.dismissUploadError();
assertStrictEqual(fileService.getUploadState(), null, 'dismissUploadError clears error banner');

// Restore original methods
apiService.uploadFile = originalUploadFile;
apiService.getFiles = originalGetFiles;
fileService.reset();

console.log('  ✓ PASS: FileService handles upload errors, retention for retry, and user dismissal.');

console.log('\n=== All File Upload & Drag-and-Drop Tests Passed Successfully (5/5)! ===\n');
