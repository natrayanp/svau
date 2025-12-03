// BaseApi.ts
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
}

export const BASE_URL = PUBLIC_API_BASE_URL;
export const GLOBAL_MOCK = PUBLIC_GLOBAL_MOCK === 'true';
export const ALLOW_GLOBAL_MOCK_OVERRIDE = PUBLIC_GLOBAL_MOCK_OVERRIDE === 'true';

export class BaseApi {
  protected baseUrl: string;
  protected prefix: string;
  protected useMock: boolean = false;
  protected mockResponses: Record<string, any> = {};

  private inFlightRequests = new Map<string, Promise<any>>();
  private responseCache = new Map<string, { data: any; expiry: number }>();

  constructor(prefix = '', baseUrl = BASE_URL, useMock: boolean = GLOBAL_MOCK) {
    this.prefix = prefix;

    this.baseUrl = ALLOW_GLOBAL_MOCK_OVERRIDE
      ? `${baseUrl}${prefix}`
      : `${BASE_URL}${prefix}`;

    this.useMock = ALLOW_GLOBAL_MOCK_OVERRIDE ? useMock : GLOBAL_MOCK;

    console.log('BaseApi → baseUrl:', this.baseUrl);
    console.log('BaseApi → mock enabled:', this.useMock);
  }

  /**
   * Register mock endpoints
   */
  protected setMockResponses(responses: Record<string, any>) {
    this.mockResponses = responses;
  }

  /**
   * Strip query params, e.g.:
   * /roles?offset=0&limit=20 → /roles
   */
  private normalizeEndpoint(endpoint: string): string {
    return endpoint.split('?')[0];
  }

  /**
   * Extract path params + query params
   */
  private extractParams(endpoint: string): Record<string, string> {
    const params: Record<string, string> = {};

    // Extract dynamic path params
    const userMatch = endpoint.match(/\/user\/(\d+)/);
    if (userMatch) params.id = userMatch[1];

    const roleMatch = endpoint.match(/\/roles\/([^/?]+)/);
    if (roleMatch) params.role = roleMatch[1];

    // Extract query params
    const qIndex = endpoint.indexOf('?');
    if (qIndex !== -1) {
      const query = endpoint.substring(qIndex + 1);
      const sp = new URLSearchParams(query);
      sp.forEach((v, k) => (params[k] = v));
    }

    return params;
  }

  /**
   * Handle mock responses
   */
  protected async mockRequest<T>(endpoint: string): Promise<T> {
    const cleanEndpoint = this.normalizeEndpoint(endpoint);
    const handler = this.mockResponses[cleanEndpoint];

    if (!handler) {
      throw new Error(`❌ No mock response defined for ${cleanEndpoint}`);
    }

    const params = this.extractParams(endpoint);
    const result =
      typeof handler === 'function' ? handler(params) : handler;

    return new Promise<T>(resolve => setTimeout(() => resolve(result), 100));
  }

  /**
   * Main request handler (backend or mock)
   */
  async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const method = options.method || 'GET';
    const bodyKey = options.body || '';
    const cacheKey = `${endpoint}:${method}:${bodyKey}`;

    // Cache hit
    if (options.cache && this.responseCache.has(cacheKey)) {
      const c = this.responseCache.get(cacheKey)!;
      if (Date.now() < c.expiry) {
        console.log('Cache hit:', endpoint);
        return c.data;
      }
      this.responseCache.delete(cacheKey);
    }

    // Deduplication
    if (this.inFlightRequests.has(cacheKey)) {
      console.log('Joined in-flight:', endpoint);
      return this.inFlightRequests.get(cacheKey)!;
    }

    // Create request
    const requestPromise = (async () => {
      let result: T;

      if (this.useMock) {
        result = await this.mockRequest<T>(endpoint);
      } else {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
          method,
          headers: {
            'Content-Type': 'application/json',
            ...(options.headers || {})
          },
          body: options.body
        });

        if (!response.ok)
          throw new Error(`API Error ${response.status} - ${endpoint}`);

        result = (await response.json()) as T;
      }

      // Cache store
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
