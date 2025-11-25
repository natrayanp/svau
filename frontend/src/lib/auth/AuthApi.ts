// src/lib/auth/AuthApi.ts
import { BaseApi } from '../BaseApi';

// -----------------------------
// Define base URL once here
// -----------------------------
const BASE_URL = '/auth-api'; // <-- change this for prod / test easily

export interface AuthUser {
  uid: string;
  email: string;
  displayName?: string;
  photoURL?: string;
  role: 'user' | 'admin';
  emailVerified: boolean;
  createdAt: string;
  lastLoginAt?: string;
}

export type UserCreatePayload = Pick<AuthUser, 'uid' | 'email' | 'displayName' | 'role' | 'emailVerified' | 'createdAt'>;
export type UserUpdatePayload = Partial<Omit<AuthUser, 'uid' | 'createdAt'>>;

class AuthUserApi extends BaseApi {
  constructor(useMock: boolean = false) {
    super(BASE_URL, useMock); // <-- use the variable here

    // Define mock responses internally
    if (useMock) {
      this.setMockResponses({
        '/login': {
          uid: '1',
          email: 'test@example.com',
          displayName: 'Test User',
          role: 'user',
          emailVerified: true,
          createdAt: new Date().toISOString()
        },
        '/me': {
          uid: '1',
          email: 'test@example.com',
          displayName: 'Test User',
          role: 'user',
          emailVerified: true,
          createdAt: new Date().toISOString()
        },
        '/users': [
          {
            uid: '1',
            email: 'test@example.com',
            displayName: 'Test User',
            role: 'user',
            emailVerified: true,
            createdAt: new Date().toISOString()
          },
          {
            uid: '2',
            email: 'admin@example.com',
            displayName: 'Admin User',
            role: 'admin',
            emailVerified: true,
            createdAt: new Date().toISOString()
          }
        ]
      });
    }
  }

  // Auth endpoints
  login(email: string, password: string) {
    return this.request<AuthUser>('/login', { method: 'POST', body: JSON.stringify({ email, password }) });
  }

  register(userData: AuthUser & { password: string }) {
    return this.request<AuthUser>('/register', { method: 'POST', body: JSON.stringify(userData) });
  }

  getCurrentUser() {
    return this.request<AuthUser>('/me');
  }

  logout() {
    return this.request<void>('/logout', { method: 'POST' });
  }

  // User management
  createUser(userData: UserCreatePayload) {
    console.log('i am insider authapi createUser');
    return this.request<AuthUser>('/users', { method: 'POST', body: JSON.stringify(userData) });
  }

  updateUser(uid: string, userData: UserUpdatePayload) {
    return this.request<AuthUser>(`/users/${uid}`, { method: 'PUT', body: JSON.stringify(userData) });
  }

  getUser(uid: string) {
    return this.request<AuthUser>(`/users/${uid}`);
  }

  deleteUser(uid: string) {
    return this.request<{ success: boolean }>(`/users/${uid}`, { method: 'DELETE' });
  }

  updateUserRole(uid: string, role: 'user' | 'admin') {
    return this.request<AuthUser>(`/users/${uid}/role`, { method: 'PATCH', body: JSON.stringify({ role }) });
  }

  listUsers() {
    return this.request<AuthUser[]>('/users');
  }
}

// -----------------------------
// Pre-instantiated API
// -----------------------------
export const authApi = new AuthUserApi(true); // mock mode enabled
