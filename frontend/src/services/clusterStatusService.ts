/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Cluster Status Polling & Consensus Monitoring Service
 */

import { apiService } from './apiService.ts';
import type { ClusterStatusResponse, ClusterState } from '../types/api.ts';

export interface ClusterStatusResult {
  data: ClusterStatusResponse | null;
  status: ClusterState | 'UNKNOWN';
  reachable: boolean;
  latencyMs: number;
  error: string | null;
  timestamp: number;
  consecutiveFailures: number;
  currentIntervalMs: number;
}

export type ClusterStatusListener = (result: ClusterStatusResult) => void;

export interface PollingConfig {
  baseIntervalMs?: number;
  maxIntervalMs?: number;
  backoffFactor?: number;
  requestTimeoutMs?: number;
}

export class ClusterStatusService {
  private lastResult: ClusterStatusResult = {
    data: null,
    status: 'UNKNOWN',
    reachable: false,
    latencyMs: 0,
    error: null,
    timestamp: Date.now(),
    consecutiveFailures: 0,
    currentIntervalMs: 500,
  };

  private listeners: Set<ClusterStatusListener> = new Set();
  private timerId: ReturnType<typeof setTimeout> | null = null;
  private abortController: AbortController | null = null;
  private isPolling = false;

  private baseIntervalMs = 500;
  private maxIntervalMs = 10000;
  private backoffFactor = 1.5;
  private requestTimeoutMs = 2000;

  /**
   * Fetches cluster status from the backend, tracks latency,
   * updates failure backoff counters, and broadcasts to listeners.
   */
  public async fetchClusterStatus(): Promise<ClusterStatusResult> {
    const start = performance.now();
    this.abortController = new AbortController();

    try {
      const data = await apiService.getClusterStatus({
        timeoutMs: this.requestTimeoutMs,
        signal: this.abortController.signal,
      });
      const latencyMs = Math.round(performance.now() - start);

      this.lastResult = {
        data,
        status: data.cluster_state,
        reachable: true,
        latencyMs,
        error: null,
        timestamp: Date.now(),
        consecutiveFailures: 0,
        currentIntervalMs: this.baseIntervalMs,
      };
    } catch (err: unknown) {
      const latencyMs = Math.round(performance.now() - start);
      const errorMsg = err instanceof Error ? err.message : 'Cluster status query failed';
      const failures = this.lastResult.consecutiveFailures + 1;
      const nextInterval = this.calculateBackoffInterval(failures);

      this.lastResult = {
        data: null,
        status: 'UNKNOWN',
        reachable: false,
        latencyMs,
        error: errorMsg,
        timestamp: Date.now(),
        consecutiveFailures: failures,
        currentIntervalMs: nextInterval,
      };
    } finally {
      this.abortController = null;
    }

    this.notifyListeners();
    return this.lastResult;
  }

  /**
   * Calculates exponential backoff delay based on consecutive failure count.
   */
  public calculateBackoffInterval(consecutiveFailures: number): number {
    if (consecutiveFailures <= 0) {
      return this.baseIntervalMs;
    }
    const exponentialDelay = this.baseIntervalMs * Math.pow(this.backoffFactor, consecutiveFailures);
    return Math.min(Math.round(exponentialDelay), this.maxIntervalMs);
  }

  /**
   * Starts the recursive polling loop matched to the heartbeat cadence.
   * Uses single-flight timeout scheduling to prevent request pile-up and hammer protection.
   */
  public startPolling(config: PollingConfig | number = 500): void {
    if (typeof config === 'number') {
      this.baseIntervalMs = config;
    } else if (config) {
      this.baseIntervalMs = config.baseIntervalMs ?? 500;
      this.maxIntervalMs = config.maxIntervalMs ?? 10000;
      this.backoffFactor = config.backoffFactor ?? 1.5;
      this.requestTimeoutMs = config.requestTimeoutMs ?? 2000;
    }

    this.stopPolling();
    this.isPolling = true;

    const executePoll = async () => {
      if (!this.isPolling) return;

      await this.fetchClusterStatus();

      if (!this.isPolling) return;

      const delay = this.lastResult.reachable
        ? this.baseIntervalMs
        : this.lastResult.currentIntervalMs;

      this.timerId = setTimeout(() => {
        void executePoll();
      }, delay);
    };

    // Trigger initial execution immediately
    void executePoll();
  }

  /**
   * Stops polling, aborts any pending request, and clears timers.
   * Prevents memory leaks on component unmount or view teardown.
   */
  public stopPolling(): void {
    this.isPolling = false;

    if (this.timerId !== null) {
      clearTimeout(this.timerId);
      this.timerId = null;
    }

    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

  /**
   * Subscribes a listener callback to cluster status updates.
   * Immediately provides current known state, and returns an unsubscribe cleanup function.
   */
  public subscribe(listener: ClusterStatusListener): () => void {
    this.listeners.add(listener);
    listener(this.lastResult);
    return () => {
      this.listeners.delete(listener);
    };
  }

  /**
   * Returns the most recent cluster status polling result.
   */
  public getLastResult(): ClusterStatusResult {
    return this.lastResult;
  }

  /**
   * Checks whether the polling loop is actively running.
   */
  public isRunning(): boolean {
    return this.isPolling;
  }

  /**
   * Resets internal state (useful for tests and mock resets).
   */
  public reset(): void {
    this.stopPolling();
    this.lastResult = {
      data: null,
      status: 'UNKNOWN',
      reachable: false,
      latencyMs: 0,
      error: null,
      timestamp: Date.now(),
      consecutiveFailures: 0,
      currentIntervalMs: this.baseIntervalMs,
    };
    this.listeners.clear();
  }

  private notifyListeners(): void {
    for (const listener of this.listeners) {
      try {
        listener(this.lastResult);
      } catch (err) {
        console.error('Error in cluster status listener:', err);
      }
    }
  }
}

export const clusterStatusService = new ClusterStatusService();
export default clusterStatusService;
