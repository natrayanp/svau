// src/lib/auth/AuthApi.ts
import { BaseApi } from '../BaseApi';
import type { 
  LoginRequest, 
  TokenResponse, 
  UserCreateBackend, 
  UserResponseBackend,
  SuccessResponseBackend 
} from './types';

// Helper functions for snake_case/camelCase conversion
const toSnakeCase = (obj: any): any => {
  if (Array.isArray(obj)) {
    return obj.map(toSnakeCase);
  } else if (obj !== null && typeof obj === 'object') {
    return Object.keys(obj).reduce((acc: any, key: string) => {
      const snakeKey = key.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`);
      acc[snakeKey] = toSnakeCase(obj[key]);
      return acc;
    }, {});
  }
  return obj;
};

const toCamelCase = (obj: any): any => {
  if (Array.isArray(obj)) {
    return obj.map(toCamelCase);
  } else if (obj !== null && typeof obj === 'object') {
    return Object.keys(obj).reduce((acc: any, key: string) => {
      const camelKey = key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
      acc[camelKey] = toCamelCase(obj[key]);
      return acc;
    }, {});
  }
  return obj;
};

export class AuthApi extends BaseApi {
  constructor() {
    super('/auth-api');
    
    // No need to set public endpoints here - they're already in BaseApi
    console.log('AuthApi initialized with public endpoints:', this.getPublicEndpoints());
  }

  /**
   * POST /auth-api/login
   * This is a public endpoint (no auth token needed)
   */
  async loginWithFirebase(firebaseToken: string): Promise<TokenResponse> {
    const loginRequest: LoginRequest = { firebase_token: firebaseToken };
    
    return this.request<TokenResponse>('/login', {
      method: 'POST',
      body: JSON.stringify(loginRequest),
      cache: false
    });
  }

  /**
   * POST /auth-api/register
   * This is a public endpoint (no auth token needed)
   */
  async registerUser(userData: UserCreateBackend): Promise<UserResponseBackend> {
    return this.request<UserResponseBackend>('/register', {
      method: 'POST',
      body: JSON.stringify(userData),
      cache: false
    });
  }

  /**
   * GET /auth-api/me
   * This is a PRIVATE endpoint (requires auth token)
   * BaseApi will automatically add the Bearer token
   */
  async getCurrentUser(): Promise<UserResponseBackend> {
    return this.request<UserResponseBackend>('/me', {
      cache: true,
      cacheTTL: 30000 // 30 seconds
    });
  }

  /**
   * POST /auth-api/logout
   * This is a public endpoint (no auth token needed)
   */
  async logout(): Promise<SuccessResponseBackend> {
    return this.request<SuccessResponseBackend>('/logout', {
      method: 'POST',
      cache: false
    });
  }

  /**
   * POST /auth-api/refresh
   * This is a public endpoint (no auth token needed)
   */
  async refreshToken(): Promise<TokenResponse> {
    return this.request<TokenResponse>('/refresh', {
      method: 'POST',
      cache: false
    });
  }

  /**
   * PUT /auth-api/me
   * This is a PRIVATE endpoint (requires auth token)
   */
  async updateCurrentUserProfile(updates: any): Promise<UserResponseBackend> {
    const snakeCaseUpdates = toSnakeCase(updates);
    return this.request<UserResponseBackend>('/me', {
      method: 'PUT',
      body: JSON.stringify(snakeCaseUpdates),
      cache: false
    });
  }

  /**
   * DELETE /auth-api/me
   * This is a PRIVATE endpoint (requires auth token)
   */
  async deleteCurrentUser(): Promise<SuccessResponseBackend> {
    return this.request<SuccessResponseBackend>('/me', {
      method: 'DELETE',
      cache: false
    });
  }

  /**
   * Health check - public endpoint
   */
  async healthCheck(): Promise<{ status: string; timestamp: string; service: string }> {
    return this.request('/health', {
      cache: true,
      cacheTTL: 60000 // 1 minute
    });
  }

  // Helper methods for conversion
  convertToFrontendUser(backendUser: UserResponseBackend): any {
    return toCamelCase(backendUser);
  }

  convertToBackendUser(frontendUser: any): UserCreateBackend {
    return toSnakeCase(frontendUser);
  }
}

// Export a singleton instance
export const authApi = new AuthApi();