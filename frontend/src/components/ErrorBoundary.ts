/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Component: ErrorBoundary (Top-Level Fault Interceptor & Crash Fallback)
 *
 * Requirements & DoD:
 * - Catches unhandled component errors to prevent blank white screen.
 * - Displays systems-grade diagnostic fallback card with error trace.
 * - Logs errors to console with structured debug context (timestamp, subsystem, telemetry).
 * - Provides retry affordance that re-attempts render without full page reload.
 */

export interface ErrorRecord {
  error: Error;
  subsystem: string;
  timestamp: number;
  isoTime: string;
  telemetrySnapshot?: Record<string, unknown>;
}

export type ErrorBoundaryListener = (record: ErrorRecord | null) => void;

export class ErrorBoundary {
  private currentError: ErrorRecord | null = null;
  private listeners: Set<ErrorBoundaryListener> = new Set();
  private retryCallbacks: Set<() => void> = new Set();

  /**
   * Captures an error, logs rich debug context to console, and notifies listeners.
   */
  public captureError(
    err: unknown,
    subsystem: string = 'AppShell',
    telemetry?: Record<string, unknown>
  ): ErrorRecord {
    const errorObj = err instanceof Error ? err : new Error(String(err));
    const now = Date.now();
    const record: ErrorRecord = {
      error: errorObj,
      subsystem,
      timestamp: now,
      isoTime: new Date(now).toISOString(),
      telemetrySnapshot: telemetry,
    };

    this.currentError = record;
    this.logError(record);
    this.notifyListeners();
    return record;
  }

  /**
   * Emits structured diagnostic context to console.error with subsystem & telemetry context.
   */
  public logError(record: ErrorRecord): void {
    console.error(`[DFSS ErrorBoundary] Unhandled exception intercepted in subsystem: [${record.subsystem}]`, {
      timestamp: record.isoTime,
      subsystem: record.subsystem,
      errorName: record.error.name,
      errorMessage: record.error.message,
      stack: record.error.stack,
      telemetrySnapshot: record.telemetrySnapshot,
    });
  }

  /**
   * Returns current captured error record or null if clean.
   */
  public getError(): ErrorRecord | null {
    return this.currentError;
  }

  /**
   * Returns true if currently in crashed/error state.
   */
  public hasError(): boolean {
    return this.currentError !== null;
  }

  /**
   * Clears the error boundary state and notifies listeners.
   */
  public reset(): void {
    this.currentError = null;
    this.notifyListeners();
  }

  /**
   * Subscribes a listener to error boundary state changes.
   */
  public subscribe(listener: ErrorBoundaryListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /**
   * Registers a callback to be invoked when user clicks Re-attempt Render.
   */
  public onRetry(callback: () => void): () => void {
    this.retryCallbacks.add(callback);
    return () => this.retryCallbacks.delete(callback);
  }

  /**
   * Dispatches all registered retry callbacks without full page reload.
   */
  public triggerRetry(): void {
    this.reset();
    for (const callback of this.retryCallbacks) {
      try {
        callback();
      } catch (err: unknown) {
        this.captureError(err, 'ErrorBoundary.retry');
      }
    }
  }

  /**
   * Safely executes a render function. Intercepts exceptions and triggers boundary fallback.
   */
  public wrap<T>(
    fn: () => T,
    subsystem: string = 'ComponentRender',
    telemetry?: Record<string, unknown>
  ): T | undefined {
    try {
      return fn();
    } catch (err: unknown) {
      this.captureError(err, subsystem, telemetry);
      return undefined;
    }
  }

  /**
   * Renders the systems-grade crash fallback markup.
   */
  public renderFallback(recordOverride?: ErrorRecord | null): string {
    const record = recordOverride ?? this.currentError;
    const errorName = record?.error?.name || 'Error';
    const errorMessage = record?.error?.message || 'An unexpected fault interrupted the UI rendering pipeline.';
    const stackTrace = record?.error?.stack || 'No stack trace available.';
    const subsystem = record?.subsystem || 'AppShell';
    const timestampStr = record?.isoTime || new Date().toISOString();

    return `
      <div class="error-boundary-container" id="error-boundary-root" role="alert" aria-live="assertive">
        <div class="error-boundary-card">
          <div class="error-boundary-header">
            <span class="badge badge-down">
              <span class="status-dot dot-down"></span> APPLICATION FAULT INTERCEPTED
            </span>
            <span class="error-boundary-subsystem font-mono text-2xs text-muted">SUBSYSTEM: ${subsystem}</span>
          </div>

          <div class="error-boundary-body">
            <h2 class="error-boundary-title font-sans">Application Execution Paused</h2>
            <p class="error-boundary-desc font-sans text-xs text-muted">
              An unhandled component exception interrupted the UI rendering engine. Distributed storage cluster nodes on ports 8000–8002 continue running normally.
            </p>

            <div class="error-boundary-diagnostics">
              <div class="error-boundary-diag-header">
                <span class="font-mono text-2xs text-ink font-semibold">${errorName}: ${errorMessage}</span>
                <span class="font-mono text-2xs text-muted">${timestampStr}</span>
              </div>
              <pre class="error-boundary-trace font-mono text-2xs" tabindex="0">${escapeHtml(stackTrace)}</pre>
            </div>
          </div>

          <div class="error-boundary-actions">
            <button
              type="button"
              id="btn-boundary-retry"
              class="btn-boundary-action btn-boundary-primary"
              title="Re-attempt rendering without reloading page"
            >
              Re-attempt Render
            </button>
            <button
              type="button"
              id="btn-boundary-reset"
              class="btn-boundary-action btn-boundary-secondary"
              title="Reset cached UI telemetry and re-fetch"
            >
              Reset Telemetry State
            </button>
          </div>
        </div>
      </div>
    `;
  }

  private notifyListeners(): void {
    for (const listener of this.listeners) {
      try {
        listener(this.currentError);
      } catch (e) {
        console.error('[DFSS ErrorBoundary] Error in listener callback:', e);
      }
    }
  }
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

export const errorBoundary = new ErrorBoundary();
