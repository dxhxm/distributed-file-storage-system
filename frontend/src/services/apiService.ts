/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Central API Service
 */

import {
  DistributedStorageClient,
  createClient,
} from '../api/client.ts';
import type {
  HealthResponse,
  ClusterStatusResponse,
  NodesResponse,
  NodeDetailResponse,
  FilesResponse,
  ClientConfig,
} from '../types/api.ts';

class ApiService {
  private client: DistributedStorageClient;
  private currentBaseUrl: string;

  constructor(config?: ClientConfig) {
    // Default to relative base URL in browser (leveraging proxy) or http://localhost:8000
    const defaultUrl = typeof window !== 'undefined' && window.location.origin.includes(':5173')
      ? ''
      : 'http://localhost:8000';
    
    this.currentBaseUrl = config?.baseUrl ?? defaultUrl;
    this.client = createClient({
      baseUrl: this.currentBaseUrl,
      defaultTimeoutMs: config?.defaultTimeoutMs ?? 3000,
      fetchImpl: config?.fetchImpl,
    });
  }

  public setBaseUrl(url: string): void {
    this.currentBaseUrl = url;
    this.client = createClient({
      baseUrl: url,
    });
  }

  public getBaseUrl(): string {
    return this.currentBaseUrl;
  }

  public async getHealth(): Promise<HealthResponse> {
    return this.client.getHealth();
  }

  public async getClusterStatus(): Promise<ClusterStatusResponse> {
    return this.client.getClusterStatus();
  }

  public async getNodes(): Promise<NodesResponse> {
    return this.client.getNodes();
  }

  public async getNodeById(nodeId: string): Promise<NodeDetailResponse> {
    return this.client.getNodeById(nodeId);
  }

  public async getFiles(): Promise<FilesResponse> {
    return this.client.getFiles();
  }

  public getRawClient(): DistributedStorageClient {
    return this.client;
  }
}

export const apiService = new ApiService();
export default apiService;
