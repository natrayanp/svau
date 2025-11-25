import { writable, derived } from 'svelte/store';
import type { Writable } from 'svelte/store';
import { auth } from './firebase';
import { onAuthStateChanged, User as FirebaseUser } from 'firebase/auth';
import { browser } from '$app/environment';
import type { ApiUser } from './types';

// ------------------------------
// Persistent store utility
// ------------------------------
function persistentStore<T>(key: string, initialValue: T): Writable<T> {
  if (!browser) return writable(initialValue);

  const stored = localStorage.getItem(key);
  const value = stored ? (JSON.parse(stored) as T) : initialValue;

  const store = writable(value);

  store.subscribe((v) => localStorage.setItem(key, JSON.stringify(v)));

  return store;
}

// ------------------------------
// Main stores
// ------------------------------
export const user: Writable<ApiUser | null> = writable(null);
export const isAuthenticated: Writable<boolean> = writable(false);
export const authLoading: Writable<boolean> = writable(true);
export const lastAuthAction: Writable<'login' | 'logout' | null> = writable(null);

// ------------------------------
// Persistent preferences
// ------------------------------
export const userPreferences = persistentStore('userPreferences', {
  theme: 'light',
  notifications: true,
  language: 'en'
});

// ------------------------------
// Derived stores
// ------------------------------
export const userDisplayName = derived(user, ($user) =>
  $user?.displayName || $user?.email.split('@')[0] || 'User'
);

export const isAdmin = derived(user, ($user) => $user?.role === 'admin');

export const isEmailVerified = derived(user, ($user) => $user?.emailVerified ?? false);

// ------------------------------
// Auth state listener
// ------------------------------
if (browser) {
  onAuthStateChanged(auth, async (firebaseUser: FirebaseUser | null) => {
    authLoading.set(true);
    console.log('indide outhstatechanged');
    try {
      if (firebaseUser) {
        const userData: ApiUser = {
          uid: firebaseUser.uid,
          email: firebaseUser.email ?? '',
          displayName: firebaseUser.displayName ?? '',
          photoURL: firebaseUser.photoURL ?? '',
          role: 'user', // default role
          emailVerified: firebaseUser.emailVerified,
          createdAt: firebaseUser.metadata.creationTime ?? '',
          lastLoginAt: firebaseUser.metadata.lastSignInTime ?? ''
        };

        user.set(userData);
        isAuthenticated.set(true);
        lastAuthAction.set('login');
        console.log('User authenticated:', userData);
      } else {
        user.set(null);
        isAuthenticated.set(false);
        lastAuthAction.set('logout');
      }
    } catch (error) {
      console.error('Auth state change error:', error);
      user.set(null);
      isAuthenticated.set(false);
    } finally {
      authLoading.set(false);
    }
  });
}

// ------------------------------
// Utility functions
// ------------------------------
export const authStore = {
  clearAuthData() {
    user.set(null);
    isAuthenticated.set(false);
    lastAuthAction.set(null);
  },

  updateUserProfile(updates: Partial<ApiUser>) {
    user.update((current) => ({ ...current!, ...updates }));
  }
};
