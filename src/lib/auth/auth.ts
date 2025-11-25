import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  updateProfile,
  sendEmailVerification,
  updatePassword,
  reauthenticateWithCredential,
  EmailAuthProvider,
  User as FirebaseUser
} from 'firebase/auth';
import { auth } from './firebase';
import { authApi } from './AuthApi';
import type { ApiUser, UserCreatePayload } from './types';
export class AuthError extends Error {
  constructor(public code: string, message: string) {
    super(message);
    this.name = 'AuthError';
  }
}

export const authService = {
  async login(email: string, password: string): Promise<FirebaseUser> {
    try {
      const userCredential = await signInWithEmailAndPassword(auth, email, password);

      if (!userCredential.user.emailVerified) {
        console.warn('User email not verified');
      }

      return userCredential.user;
    } catch (error: any) {
      throw new AuthError(error.code ?? 'auth/unknown-error', this.getFriendlyErrorMessage(error));
    }
  },

  async register(email: string, password: string, displayName?: string): Promise<FirebaseUser> {
    console.log('i am insider register');
    try {
      const userCredential = await createUserWithEmailAndPassword(auth, email, password);

      if (displayName?.trim()) {
        await updateProfile(userCredential.user, { displayName: displayName.trim() });
      }

      await sendEmailVerification(userCredential.user);
        console.log('i am insider register4');

      const payload: UserCreatePayload = {
        uid: userCredential.user.uid,
        email,
        displayName: displayName?.trim(),
        role: 'user',
        emailVerified: false,
        createdAt: new Date().toISOString()
      };

      await authApi.createUser(payload);
        console.log('i am insider register5');

      return userCredential.user;
    } catch (error: any) {
       console.log('i am insider register error');
      throw new AuthError(error.code ?? 'auth/unknown-error', this.getFriendlyErrorMessage(error));
    }
  },

  async logout(): Promise<void> {
    try {
      await signOut(auth);
    } catch (error: any) {
      throw new AuthError(error.code ?? 'auth/unknown-error', 'Failed to logout. Please try again.');
    }
  },

  async updateUserProfile(updates: Partial<ApiUser>): Promise<void> {
    const user = auth.currentUser;
    if (!user) throw new AuthError('auth/no-user', 'No authenticated user');

    const updatePromises: Promise<void>[] = [];

    if (updates.displayName && updates.displayName !== user.displayName) {
      updatePromises.push(updateProfile(user, { displayName: updates.displayName }));
    }

    if (updates.photoURL && updates.photoURL !== user.photoURL) {
      updatePromises.push(updateProfile(user, { photoURL: updates.photoURL }));
    }

    await Promise.all(updatePromises);

    await authApi.updateUser(user.uid, updates);
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    const user = auth.currentUser;
    if (!user || !user.email) throw new AuthError('auth/no-user', 'No authenticated user or email');

    const credential = EmailAuthProvider.credential(user.email, currentPassword);
    await reauthenticateWithCredential(user, credential);
    await updatePassword(user, newPassword);
  },

  async resendEmailVerification(): Promise<void> {
    const user = auth.currentUser;
    if (!user) throw new AuthError('auth/no-user', 'No authenticated user');

    await sendEmailVerification(user);
  },

  getFriendlyErrorMessage(error: any): string {
    const map: Record<string, string> = {
      'auth/invalid-email': 'Please enter a valid email address.',
      'auth/user-disabled': 'This account has been disabled.',
      'auth/user-not-found': 'No account found with this email.',
      'auth/wrong-password': 'Incorrect password. Please try again.',
      'auth/email-already-in-use': 'An account with this email already exists.',
      'auth/weak-password': 'Password should be at least 6 characters long.',
      'auth/network-request-failed': 'Network error. Please check your connection.',
      'auth/too-many-requests': 'Too many attempts. Please try again later.',
      'auth/requires-recent-login': 'Please login again to perform this action.'
    };

    return map[error.code] ?? error.message ?? 'An unexpected error occurred.';
  },

  validateEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  },

  validatePassword(password: string): boolean {
    return password.length >= 6;
  },

  validateDisplayName(displayName?: string): boolean {
    return !!displayName && displayName.trim().length >= 2;
  }
};
