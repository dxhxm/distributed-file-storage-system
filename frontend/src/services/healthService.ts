/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Health & Backend Reachability Monitoring Service
 */

import { apiService } from './apiService.ts';
import type { HealthResponse } from '../types/api.ts';

export type ConnectivityStatus = 'CONNECTED' | 'DEGRADED' | 'DISCONNECTED' | 'CHECKING';

export interface HealthCheckResult {
  reachable: boolean;
  status: ConnectivityStatus;
  latencyMs: number;
  data: HealthResponse | null;
  error: string | null;
  timestamp: number;
  consecutiveFailures: number;
  currentIntervalMs: number;
}

export type HealthListener = (result: HealthCheckResult) => void;

export interface HealthPollingConfig {
  intervalMs?: number; // legacy alias
  baseIntervalMs?: number;
  maxIntervalMs?: number;
  backoffFactor?: number;
}

export class HealthService {
  private lastResult: HealthCheckResult = {
    reachable: false,
    status: 'CHECKING',
    latencyMs: 0,
    data: null,
    error: null,
    timestamp: Date.now(),
    consecutiveFailures: 0,
    currentIntervalMs: 3000,
  };

  private listeners: Set<HealthListener> = new Set();
  private timerId: ReturnType<typeof setTimeout> | null = null;
  private isPolling = false;

  private baseIntervalMs = 3000;
  private maxIntervalMs = 15000;
  private backoffFactor = 1.5;
  private consecutiveFailures = 0;
  private currentIntervalMs = 3000;

  public async checkHealth(): Promise<HealthCheckResult> {
    const start = performance.now();
    try {
      const data = await apiService.getHealth();
      const latencyMs = Math.round(performance.now() - start);

      this.consecutiveFailures = 0;
      this.currentIntervalMs = this.baseIntervalMs;

      this.lastResult = {
        reachable: true,
        status: latencyMs > 1000 ? 'DEGRADED' : 'CONNECTED',
        latencyMs,
        data,
        error: null,
        timestamp: Date.now(),
        consecutiveFailures: 0,
        currentIntervalMs: this.baseIntervalMs,
      };
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Backend unreachable';
      this.consecutiveFailures++;
      this.currentIntervalMs = this.calculateBackoffInterval(this.consecutiveFailures);

      this.lastResult = {
        reachable: false,
        status: 'DISCONNECTED',
        latencyMs: 0,
        data: null,
        error: errorMsg,
        timestamp: Date.now(),
        consecutiveFailures: this.consecutiveFailures,
        currentIntervalMs: this.currentIntervalMs,
      };
    }

    this.notifyListeners();
    return this.lastResult;
  }

  public async retry(): Promise<HealthCheckResult> {
    this.consecutiveFailures = 0;
    this.currentIntervalMs = this.baseIntervalMs;
    return this.checkHealth();
  }

  public calculateBackoffInterval(failures: number): number {
    if (failures <= 0) return this.baseIntervalMs;
    const delay = this.baseIntervalMs * Math.pow(this.backoffFactor, failures);
    return Math.min(Math.round(delay), this.maxIntervalMs);
  }

  public startPolling(config: HealthPollingConfig | number = 3000): void {
    if (typeof config === 'number') {
      this.baseIntervalMs = config;
      this.currentIntervalMs = config;
    } else if (config) {
      this.baseIntervalMs = config.baseIntervalMs ?? config.intervalMs ?? 3000;
      this.maxIntervalMs = config.maxIntervalMs ?? 15000;
      this.backoffFactor = config.backoffFactor ?? 1.5;
      this.currentIntervalMs = this.baseIntervalMs;
    }

    this.stopPolling();
    this.isPolling = true;

    const executeLoop = async () => {
      if (!this.isPolling) return;
      await this.checkHealth();
      if (!this.isPolling) return;

      const delay = this.lastResult.reachable
        ? this.baseIntervalMs
        : this.lastResult.currentIntervalMs;

      this.timerId = setTimeout(() => {
        void executeLoop();
      }, delay);
    };

    void executeLoop();
  }

  public stopPolling(): void {
    this.isPolling = false;
    if (this.timerId !== null) {
      clearTimeout(this.timerId);
      this.timerId = null;
    }
  }

  public subscribe(listener: HealthListener): () => void {
    this.listeners.add(listener);
    // Send immediate current state
    listener(this.lastResult);
    return () => {
      this.listeners.delete(listener);
    };
  }

  public getLastResult(): HealthCheckResult {
    return this.lastResult;
  }

  public isRunning(): boolean {
    return this.isPolling;
  }

  public reset(): void {
    this.stopPolling();
    this.consecutiveFailures = 0;
    this.currentIntervalMs = this.baseIntervalMs;
    this.lastResult = {
      reachable: false,
      status: 'CHECKING',
      latencyMs: 0,
      data: null,
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
        console.error('Error in health listener:', err);
      }
    }
  }
}

export const healthService = new HealthService();
export default healthService;
