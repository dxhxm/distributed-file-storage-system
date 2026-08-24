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
}

export type HealthListener = (result: HealthCheckResult) => void;

class HealthService {
  private lastResult: HealthCheckResult = {
    reachable: false,
    status: 'CHECKING',
    latencyMs: 0,
    data: null,
    error: null,
    timestamp: Date.now(),
  };

  private listeners: Set<HealthListener> = new Set();
  private pollIntervalId: ReturnType<typeof setInterval> | null = null;

  public async checkHealth(): Promise<HealthCheckResult> {
    const start = performance.now();
    try {
      const data = await apiService.getHealth();
      const latencyMs = Math.round(performance.now() - start);

      this.lastResult = {
        reachable: true,
        status: latencyMs > 1000 ? 'DEGRADED' : 'CONNECTED',
        latencyMs,
        data,
        error: null,
        timestamp: Date.now(),
      };
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Backend unreachable';
      this.lastResult = {
        reachable: false,
        status: 'DISCONNECTED',
        latencyMs: 0,
        data: null,
        error: errorMsg,
        timestamp: Date.now(),
      };
    }

    this.notifyListeners();
    return this.lastResult;
  }

  public startPolling(intervalMs: number = 2000): void {
    if (this.pollIntervalId) {
      clearInterval(this.pollIntervalId);
    }
    // Perform immediate check
    void this.checkHealth();
    this.pollIntervalId = setInterval(() => {
      void this.checkHealth();
    }, intervalMs);
  }

  public stopPolling(): void {
    if (this.pollIntervalId) {
      clearInterval(this.pollIntervalId);
      this.pollIntervalId = null;
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
