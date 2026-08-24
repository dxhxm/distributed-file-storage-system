/**
 * Distributed Fault-Tolerant File Storage System (DFSS)
 * Client-Side Hash Router
 */

export type RouteHandler = (params?: Record<string, string>) => void;

export interface RouteDefinition {
  path: string;
  handler: RouteHandler;
}

class Router {
  private routes: Map<string, RouteHandler> = new Map();
  private notFoundHandler: RouteHandler = () => {
    console.warn('Route not found');
  };
  private currentPath: string = '';

  constructor() {
    if (typeof window !== 'undefined') {
      window.addEventListener('hashchange', () => this.handleRouteChange());
    }
  }

  public addRoute(path: string, handler: RouteHandler): this {
    this.routes.set(path, handler);
    return this;
  }

  public setNotFound(handler: RouteHandler): this {
    this.notFoundHandler = handler;
    return this;
  }

  public navigate(path: string): void {
    if (typeof window !== 'undefined') {
      window.location.hash = path.startsWith('#') ? path : `#${path}`;
    }
  }

  public getCurrentPath(): string {
    if (typeof window === 'undefined') return '/';
    const hash = window.location.hash.slice(1);
    return hash || '/';
  }

  public getActiveRoute(): string {
    return this.currentPath;
  }

  public start(): void {
    this.handleRouteChange();
  }

  private handleRouteChange(): void {
    const rawPath = this.getCurrentPath();
    this.currentPath = rawPath;

    // Match exact route
    const handler = this.routes.get(rawPath);
    if (handler) {
      handler();
      return;
    }

    // Default route match
    if (rawPath === '' || rawPath === '/') {
      const defaultHandler = this.routes.get('/') || this.routes.get('/dashboard');
      if (defaultHandler) {
        defaultHandler();
        return;
      }
    }

    this.notFoundHandler();
  }
}

export const router = new Router();
export default router;
