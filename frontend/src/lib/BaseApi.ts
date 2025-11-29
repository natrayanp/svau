
export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  headers?: Record<string, string>;
  body?: string;
  cache?: boolean;        // Enable caching
  cacheTTL?: number;      // Time-to-live in ms for cached responses
}

export const BASE_URL = '/api';

export class BaseApi {
  protected baseUrl: string;
  protected useMock: boolean = false;
  protected mockResponses: Record<string, any> = {};

  // ✅ GLOBAL MOCK CONTROL VARIABLE
  private static globalMockEnabled: boolean = true;

  // ✅ Deduplication and caching maps
  private inFlightRequests: Map<string, Promise<any>> = new Map();
  private responseCache: Map<string, { data: any; expiry: number }> = new Map();

  constructor(baseUrl: string = BASE_URL, useMock: boolean = false) {
    this.baseUrl = baseUrl;
    // ✅ Use global mock setting by default, allow override
    //this.useMock = useMock ?? BaseApi.globalMockEnabled;
    this.useMock = true;
  }

  protected setMockResponses(responses: Record<string, any>) {
    this.mockResponses = responses;
  }

  /**
   * ✅ Handles mock responses (function or object)
   */
  protected async mockRequest<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    console.log('Mock request for endpoint:', endpoint);

    const mockHandler = this.mockResponses[endpoint];
    if (!mockHandler) {
      throw new Error(`No mock response defined for ${endpoint}`);
    }

    // If mock is a function, call it with params extracted from endpoint
    const params = this.extractParams(endpoint);
    const mockResponse = typeof mockHandler === 'function' ? mockHandler(params) : mockHandler;

    console.log('[Mock API Response]', mockResponse);

    return new Promise<T>((resolve) => setTimeout(() => resolve(mockResponse as T), 100));
  }

  /**
   * ✅ Extract dynamic params from endpoint (e.g., /user/123 → { id: 123 })
   */
  private extractParams(endpoint: string): Record<string, string> {
    const params: Record<string, string> = {};
    const userMatch = endpoint.match(/\/user\/(\d+)/);
    const roleMatch = endpoint.match(/\/roles\/([^/]+)/);

    if (userMatch) params.id = userMatch[1];
    if (roleMatch) params.role = roleMatch[1];

    return params;
  }

  /**
   * ✅ Main request method with caching and deduplication
   */
  async request<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    const method = options?.method || 'GET';
    const bodyKey = options?.body || '';
    const cacheKey = `${endpoint}:${method}:${bodyKey}`;

    // ✅ Check cache
    if (options?.cache && this.responseCache.has(cacheKey)) {
      const cached = this.responseCache.get(cacheKey)!;
      if (Date.now() < cached.expiry) {
        console.log(`Returning cached response for ${endpoint}`);
        return cached.data;
      } else {
        this.responseCache.delete(cacheKey); // Expired
      }
    }

    // ✅ Deduplication: return in-flight request if exists
    if (this.inFlightRequests.has(cacheKey)) {
      console.log(`Joining in-flight request for ${endpoint}`);
      return this.inFlightRequests.get(cacheKey)!;
    }

    // ✅ Create new request promise
    const requestPromise = (async () => {
      let result: T;

      if (this.useMock) {
        result = await this.mockRequest<T>(endpoint, options);
      } else {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
          headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) },
          ...options
        });

        if (!response.ok) throw new Error(`API error: ${response.status}`);
        result = await response.json() as T;
      }

      // ✅ Cache response if enabled
      if (options?.cache) {
        const ttl = options.cacheTTL || 30000; // Default 30s
        this.responseCache.set(cacheKey, { data: result, expiry: Date.now() + ttl });
      }

      return result;
    })();

    this.inFlightRequests.set(cacheKey, requestPromise);

    try {
      const result = await requestPromise;
      return result;
    } finally {
      this.inFlightRequests.delete(cacheKey);
    }
  }
}
