import { apiService } from './apiService.ts';
import type { NodeState, NodeStatus } from '../types/api.ts';

export type PulseTickType = 'ok' | 'warn' | 'missed';


export interface NodeHeartbeatState {
  id: string;
  displayName: string;
  state: NodeState;
  status: NodeStatus;
  lastHeartbeat: number;
  latencyMs: number;
  url?: string;
  port: string;
  isPulsing: boolean;
  history: PulseTickType[];
  consecutiveMissed: number;
}

export interface HeartbeatRailResult {
  nodes: NodeHeartbeatState[];
  reachable: boolean;
  timestamp: number;
  error: string | null;
}

export type HeartbeatListener = (result: HeartbeatRailResult) => void;

export interface HeartbeatPollingConfig {
  intervalMs?: number;
  maxHistoryTicks?: number;
  requestTimeoutMs?: number;
}

const MAX_HISTORY_TICKS = 20;

function extractPort(url?: string, fallbackId?: string): string {
  if (url) {
    try {
      const parsed = new URL(url);
      if (parsed.port) return `:${parsed.port}`;
    } catch {
      // url might be partial
    }
  }
  if (fallbackId?.includes('8000') || fallbackId?.toLowerCase().includes('a')) return ':8000';
  if (fallbackId?.includes('8001') || fallbackId?.toLowerCase().includes('b')) return ':8001';
  if (fallbackId?.includes('8002') || fallbackId?.toLowerCase().includes('c')) return ':8002';
  return ':8000';
}

function normalizeNodeKey(id: string): string {
  return id.replace(/\s+/g, '').replace(/^node/i, 'node');
}

export class HeartbeatService {
  private nodeMap: Map<string, NodeHeartbeatState> = new Map();
  private listeners: Set<HeartbeatListener> = new Set();
  private timerId: ReturnType<typeof setTimeout> | null = null;
  private abortController: AbortController | null = null;
  private isPolling = false;

  private intervalMs = 500;
  private requestTimeoutMs = 2000;
  private maxHistoryTicks = MAX_HISTORY_TICKS;

  private lastResult: HeartbeatRailResult = {
    nodes: [],
    reachable: false,
    timestamp: Date.now(),
    error: null,
  };

  constructor() {
    this.initializeDefaultNodes();
  }

  private initializeDefaultNodes(): void {
    const defaultKeys = [
      { id: 'nodeA', displayName: 'nodeA', state: 'LEADER' as NodeState, port: ':8000', offset: 0.0 },
      { id: 'nodeB', displayName: 'nodeB', state: 'FOLLOWER' as NodeState, port: ':8001', offset: 8.4 },
      { id: 'nodeC', displayName: 'nodeC', state: 'FOLLOWER' as NodeState, port: ':8002', offset: 12.1 },
    ];

    for (const def of defaultKeys) {
      this.nodeMap.set(def.id, {
        id: def.id,
        displayName: def.displayName,
        state: def.state,
        status: 'ONLINE',
        lastHeartbeat: Date.now() / 1000,
        latencyMs: def.offset,
        port: def.port,
        isPulsing: false,
        history: Array(MAX_HISTORY_TICKS).fill('ok'),
        consecutiveMissed: 0,
      });
    }

    this.lastResult.nodes = Array.from(this.nodeMap.values());
  }

  /**
   * Fetches latest /nodes status from backend and updates pulse tick histories.
   */
  public async pollHeartbeats(): Promise<HeartbeatRailResult> {
    const start = performance.now();
    this.abortController = new AbortController();

    try {
      const response = await apiService.getNodes({
        timeoutMs: this.requestTimeoutMs,
        signal: this.abortController.signal,
      });
      const latencyMs = Math.round(performance.now() - start);

      const rawNodes = response.nodes || [];
      const updatedNodes: NodeHeartbeatState[] = [];

      for (const raw of rawNodes) {
        const key = normalizeNodeKey(raw.id);
        const existing = this.nodeMap.get(key) || {
          id: key,
          displayName: raw.id,
          state: raw.state,
          status: raw.status,
          lastHeartbeat: raw.last_heartbeat,
          latencyMs: 0,
          port: extractPort(raw.url, raw.id),
          isPulsing: false,
          history: Array(this.maxHistoryTicks).fill('ok'),
          consecutiveMissed: 0,
        };

        const isOnline = raw.status === 'ONLINE';
        const heartbeatAdvanced = raw.last_heartbeat > existing.lastHeartbeat;
        const recentHeartbeat = (Date.now() / 1000 - raw.last_heartbeat) < 5.0;

        // Slide history window
        const nextHistory = [...existing.history];
        let tickType: PulseTickType = 'ok';
        let isPulsing = false;

        if (isOnline && (heartbeatAdvanced || recentHeartbeat)) {
          tickType = 'ok';
          isPulsing = true;
          existing.consecutiveMissed = 0;
        } else if (isOnline) {
          tickType = 'warn';
          isPulsing = false;
          existing.consecutiveMissed++;
        } else {
          // OFFLINE: Pulse is strictly stalled
          tickType = 'missed';
          isPulsing = false;
          existing.consecutiveMissed++;
        }

        nextHistory.push(tickType);
        if (nextHistory.length > this.maxHistoryTicks) {
          nextHistory.shift();
        }

        const nodeState: NodeHeartbeatState = {
          id: key,
          displayName: raw.id,
          state: raw.state,
          status: raw.status,
          lastHeartbeat: raw.last_heartbeat,
          latencyMs: isOnline ? (raw.state === 'LEADER' ? 0.0 : (latencyMs || (key === 'nodeB' ? 8.4 : 12.1))) : 0,
          url: raw.url,
          port: extractPort(raw.url, raw.id),
          isPulsing,
          history: nextHistory,
          consecutiveMissed: existing.consecutiveMissed,
        };


        this.nodeMap.set(key, nodeState);
        updatedNodes.push(nodeState);
      }

      this.lastResult = {
        nodes: updatedNodes.length > 0 ? updatedNodes : Array.from(this.nodeMap.values()),
        reachable: true,
        timestamp: Date.now(),
        error: null,
      };
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to query nodes';
      
      // On connection error, mark all nodes with missed ticks
      for (const [key, node] of this.nodeMap.entries()) {
        const nextHistory = [...node.history, 'missed' as PulseTickType];
        if (nextHistory.length > this.maxHistoryTicks) {
          nextHistory.shift();
        }
        this.nodeMap.set(key, {
          ...node,
          status: 'OFFLINE',
          isPulsing: false,
          history: nextHistory,
          consecutiveMissed: node.consecutiveMissed + 1,
        });
      }

      this.lastResult = {
        nodes: Array.from(this.nodeMap.values()),
        reachable: false,
        timestamp: Date.now(),
        error: errorMsg,
      };
    } finally {
      this.abortController = null;
    }

    this.notifyListeners();
    return this.lastResult;
  }

  /**
   * Starts periodic polling loop for heartbeat telemetry.
   */
  public startPolling(config: HeartbeatPollingConfig | number = 500): void {
    if (typeof config === 'number') {
      this.intervalMs = config;
    } else if (config) {
      this.intervalMs = config.intervalMs ?? 500;
      this.maxHistoryTicks = config.maxHistoryTicks ?? MAX_HISTORY_TICKS;
      this.requestTimeoutMs = config.requestTimeoutMs ?? 2000;
    }

    this.stopPolling();
    this.isPolling = true;

    const executeLoop = async () => {
      if (!this.isPolling) return;
      await this.pollHeartbeats();
      if (!this.isPolling) return;

      this.timerId = setTimeout(() => {
        void executeLoop();
      }, this.intervalMs);
    };

    void executeLoop();
  }

  /**
   * Stops polling, clears timers, and aborts any active fetch request.
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
   * Subscribes a listener callback to heartbeat telemetry updates.
   */
  public subscribe(listener: HeartbeatListener): () => void {
    this.listeners.add(listener);
    listener(this.lastResult);
    return () => {
      this.listeners.delete(listener);
    };
  }

  public getLastResult(): HeartbeatRailResult {
    return this.lastResult;
  }

  public isRunning(): boolean {
    return this.isPolling;
  }

  public reset(): void {
    this.stopPolling();
    this.nodeMap.clear();
    this.initializeDefaultNodes();
    this.listeners.clear();
  }

  private notifyListeners(): void {
    for (const listener of this.listeners) {
      try {
        listener(this.lastResult);
      } catch (err) {
        console.error('Error in heartbeat listener:', err);
      }
    }
  }
}

export const heartbeatService = new HeartbeatService();
export default heartbeatService;
