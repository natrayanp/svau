// src/lib/auth/authStore.ts
import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';
import type { UserFrontend } from './authtypes';

// Parse JWT to extract user data
function parseJwt(token: string): any {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
      return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

// Main auth stores
export const authUser = writable<UserFrontend | null>(null);
export const isAuthenticated = writable(false);
export const authLoading = writable(true);

// JWT token store
export const jwtToken = writable<string | null>(null);

// Initialize from localStorage and parse JWT
if (browser) {
  const token = localStorage.getItem('jwt_token');
  if (token) {
    jwtToken.set(token);
    
    // Parse JWT to get user data immediately
    const payload = parseJwt(token);
    if (payload) {
      authUser.set({
        id: payload.user_id,
        uid: payload.uid,
        email: payload.email,
        displayName: payload.display_name || payload.email?.split('@')[0] || 'User',
        role: payload.role || 'user',  // Role from JWT
        emailVerified: payload.email_verified || false,
        createdAt: payload.created_at || new Date().toISOString()
      });
      isAuthenticated.set(true);
    }
  }
}

// Derived stores for role-based permissions
export const userRole = derived(authUser, ($user) => $user?.role || null);

export const isAdmin = derived(authUser, ($user) => $user?.role === 'admin');

export const hasPermission = (requiredRole: string) => {
  return derived(authUser, ($user) => {
    if (!$user) return false;
    
    // Simple role hierarchy
    const roleHierarchy = {
      'admin': ['admin', 'moderator', 'user'],
      'moderator': ['moderator', 'user'],
      'user': ['user']
    };
    
    return roleHierarchy[$user.role]?.includes(requiredRole) || false;
  });
};