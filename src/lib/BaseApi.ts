// src/lib/api/BaseApi.ts
export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  headers?: Record<string, string>;
  body?: string;
}

// -----------------------------
// Define default base URL here
// -----------------------------
export const BASE_URL = '/api'; // <-- change once for prod / testing

export class BaseApi {
  protected baseUrl: string;
  protected useMock: boolean = false;
  protected mockResponses: Record<string, any> = {};

  constructor(baseUrl: string = BASE_URL, useMock: boolean = false) {
    this.baseUrl = baseUrl;
    this.useMock = useMock;
  }

  protected setMockResponses(responses: Record<string, any>) {
    this.mockResponses = responses;
  }

  protected async mockRequest<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    const resp = this.mockResponses[endpoint];
    if (!resp) throw new Error(`No mock response defined for ${endpoint}`);
    // Simulate async API
    return new Promise<T>((resolve) => setTimeout(() => resolve(resp as T), 100));
  }

  async request<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    if (this.useMock) return this.mockRequest<T>(endpoint, options);

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) },
      ...options
    });

    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json() as Promise<T>;
  }
}
