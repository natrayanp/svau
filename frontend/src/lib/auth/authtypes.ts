// src/lib/auth/types.ts
export interface AuthUser {
  id: number;
  uid: string;
  email: string;
  display_name: string;  // Backend uses snake_case
  role: string;          // Backend returns string, not 'user' | 'admin'
  email_verified: boolean;
  created_at: string;    // Backend uses snake_case
}

// For frontend convenience (camelCase)
export interface FrontendUser {
  id: number;
  uid: string;
  email: string;
  displayName: string;
  role: string;
  emailVerified: boolean;
  createdAt: string;
}

export interface JwtTokens {
  access_token: string;  // Backend uses snake_case
  expires_in: number;    // Backend uses snake_case
}

export interface FirebaseLoginRequest {
  firebase_token: string;  // Backend expects snake_case
}

// Backend UserCreate model
export interface UserCreateBackend {
  uid: string;
  email: string;
  display_name: string;
  role: string;
  email_verified: boolean;
}

// Frontend UserCreate model (for your convenience)
export interface UserCreateFrontend {
  uid: string;
  email: string;
  displayName: string;
  role: string;
  emailVerified: boolean;
}

// Success response from backend
export interface SuccessResponse {
  success: boolean;
  message: string;
}

export interface UserFrontend {
  id: number;
  uid: string;
  email: string;
  displayName: string;
  role: string;  // This comes from JWT/backend
  emailVerified: boolean;
  createdAt: string;
}