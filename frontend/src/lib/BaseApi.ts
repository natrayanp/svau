// BaseApi.ts
import { get } from 'svelte/store';
import { mockAuthEnabled, mockRole } from '$lib/auth/mockAuth';
import whitelist from '../../shared/whitelist.json' assert { type: 'json' };

import {
  PUBLIC_API_BASE_URL,
  PUBLIC_GLOBAL_MOCK,
  PUBLIC_GLOBAL_MOCK_OVERRIDE
} from '$env/static/public';

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  headers?: Record<string, string>;
  body?: string;
  cache?: boolean;
  cacheTTL?: number;
  requestId?: string;
}

export const BASE_URL = PUBLIC_API_BASE_URL;
export const GLOBAL_MOCK = PUBLIC_GLOBAL_MOCK === 'true';
export const ALLOW_GLOBAL_MOCK_OVERRIDE = PUBLIC_GLOBAL_MOCK_OVERRIDE === 'true';

export class BaseApi {
  protected baseUrl: string;
  protected prefix: string;
  protected useMock: boolean = false;
  protected mockResponses: Record<string, any> = {};

  // ✅ Loaded from shared JSON
  protected publicEndpoints: string[] = [...whitelist.PUBLIC_PATHS];
  protected publicPrefixes: string[] = [...whitelist.PUBLIC_PREFIXES];

  private inFlightRequests = new Map<string, Promise<any>>();
  private responseCache = new Map<string, { data: any; expiry: number }>();
  private authToken: string | null = null;

  constructor(prefix = '', baseUrl = BASE_URL, useMock: boolean = GLOBAL_MOCK) {
    this.prefix = prefix;
    this.baseUrl = ALLOW_GLOBAL_MOCK_OVERRIDE ? `${baseUrl}${prefix}` : `${BASE_URL}${prefix}`;
    this.useMock = ALLOW_GLOBAL_MOCK_OVERRIDE ? useMock : GLOBAL_MOCK;

    if (typeof window !== 'undefined') {
      this.authToken = localStorage.getItem('jwt_token');
    }

    // ✅ Prevent tree-shaking of getPublicEndpoints()
    this.getPublicEndpoints;

    console.log(`BaseApi initialized: ${this.baseUrl}, Mock: ${this.useMock}`);
  }

  // ✅ Prevent tree-shaking
  /** @no-tree-shake */
  getPublicEndpoints(): string[] {
    return [...this.publicEndpoints];
  }

  setAuthToken(token: string | null): void {
    this.authToken = token;
    if (token && typeof window !== 'undefined') {
      localStorage.setItem('jwt_token', token);
      console.log('✅ Auth token set in BaseApi');
    } else if (typeof window !== 'undefined') {
      localStorage.removeItem('jwt_token');
      console.log('🗑️ Auth token cleared from BaseApi');
    }
  }

  getAuthToken(): string | null {
    return this.authToken;
  }

  clearAuthToken(): void {
    this.setAuthToken(null);
  }

  // ✅ Uses shared whitelist.json
  private isPublicEndpoint(endpoint: string): boolean {
    const clean = endpoint.split('?')[0];

    if (this.publicEndpoints.includes(clean)) return true;
    if (this.publicPrefixes.some(prefix => clean.startsWith(prefix))) return true;

    return false;
  }

  private generateRequestId(): string {
    const prefix = 'req';
    const timestamp = Date.now();
    const microseconds = Math.floor(performance.now() * 1000) % 1000;
    const randomBytes = crypto.getRandomValues(new Uint8Array(2));
    const randomHex = Array.from(randomBytes)
      .map(b => b.toString(16).padStart(2, '0'))
      .join('');

    return `${prefix}_${timestamp}_${microseconds.toString().padStart(3, '0')}_${randomHex}`;
  }

  protected setMockResponses(responses: Record<string, any>) {
    this.mockResponses = responses;
  }

  private normalizeEndpoint(endpoint: string): string {
    return endpoint.split('?')[0];
  }

  private extractParams(endpoint: string): Record<string, string> {
    const params: Record<string, string> = {};
    const qIndex = endpoint.indexOf('?');

    if (qIndex !== -1) {
      const query = endpoint.substring(qIndex + 1);
      const sp = new URLSearchParams(query);
      sp.forEach((v, k) => (params[k] = v));
    }

    return params;
  }

  protected async mockRequest<T>(endpoint: string): Promise<T> {
    const cleanEndpoint = this.normalizeEndpoint(endpoint);
    const handler = this.mockResponses[cleanEndpoint];

    if (!handler) {
      throw new Error(`❌ No mock response defined for ${cleanEndpoint}`);
    }

    const params = this.extractParams(endpoint);
    const result = typeof handler === 'function' ? handler(params) : handler;

    return new Promise<T>(resolve => setTimeout(() => resolve(result), 100));
  }

  async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const method = options.method || 'GET';
    const bodyKey = options.body || '';
    const cacheKey = `${endpoint}:${method}:${bodyKey}`;
    const requestId = options.requestId || this.generateRequestId();

    if (options.cache && this.responseCache.has(cacheKey)) {
      const c = this.responseCache.get(cacheKey)!;
      if (Date.now() < c.expiry) {
        console.log(`BaseApi: Cache hit for ${endpoint}`);
        return c.data;
      }
      this.responseCache.delete(cacheKey);
    }

    if (this.inFlightRequests.has(cacheKey)) {
      console.log(`BaseApi: Joined in-flight request for ${endpoint}`);
      return this.inFlightRequests.get(cacheKey)!;
    }

    const requestPromise = (async () => {
      let result: T;

      if (this.useMock) {
        console.log(`BaseApi: Mock request to ${endpoint}`);
        result = await this.mockRequest<T>(endpoint);
      } else {
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
          'X-Request-ID': requestId,
          ...(options.headers || {})
        };

        // ✅ Inject mock role header
        if (get(mockAuthEnabled)) {
          headers['X-Mock-Role'] = get(mockRole);
          console.log(`BaseApi: Using mock role ${headers['X-Mock-Role']}`);
        }

        const isPublic = this.isPublicEndpoint(endpoint);

        if (this.authToken && !isPublic) {
          headers['Authorization'] = `Bearer ${this.authToken}`;
          console.log(`BaseApi: Adding auth token to ${endpoint}`);
        } else if (isPublic) {
          console.log(`BaseApi: ${endpoint} is public, skipping auth token`);
        }

        const response = await fetch(`${this.baseUrl}${endpoint}`, {
          method,
          headers,
          body: options.body,
          credentials: 'include'
        });

        if (response.status === 401 && this.authToken && !isPublic) {
          console.warn(`BaseApi: Token expired for ${endpoint}`);
          this.clearAuthToken();
          throw new Error('Authentication token expired. Please login again.');
        }

        if (!response.ok) {
          const errorText = await response.text().catch(() => 'No error details');
          console.error(`BaseApi: Request failed ${response.status} for ${endpoint}: ${errorText}`);
          throw new Error(`API Error ${response.status}: ${errorText}`);
        }

        result = (await response.json()) as T;
      }

      if (options.cache) {
        const ttl = options.cacheTTL ?? 30_000;
        this.responseCache.set(cacheKey, {
          data: result,
          expiry: Date.now() + ttl
        });
      }

      return result;
    })();

    this.inFlightRequests.set(cacheKey, requestPromise);

    try {
      return await requestPromise;
    } finally {
      this.inFlightRequests.delete(cacheKey);
    }
  }
}
