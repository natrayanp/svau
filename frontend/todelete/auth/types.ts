export interface ApiUser {
  uid: string;
  email: string;
  displayName: string;
  photoURL?: string;
  role: 'user' | 'admin';
  emailVerified: boolean;
  createdAt: string;
  lastLoginAt?: string;
  [key: string]: any; // allow extra fields if needed
}

// Payload used when creating a new user (required fields only)
export type UserCreatePayload = Pick<
  ApiUser,
  'uid' | 'email' | 'displayName' | 'role' | 'emailVerified' | 'createdAt'
>;

// Payload used when updating an existing user
export type UserUpdatePayload = Partial<Omit<ApiUser, 'uid' | 'createdAt'>>;

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface RequestOptions {
  method?: HttpMethod;
  headers?: Record<string, string>;
  body?: string;
}
