// src/lib/auth/firebaseClient.ts
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
import { auth } from './firebase'; // Your firebase config

export class FirebaseAuthClient {
  async loginWithEmailPassword(email: string, password: string): Promise<FirebaseUser> {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    return userCredential.user;
  }

  async registerWithEmailPassword(email: string, password: string, displayName?: string): Promise<FirebaseUser> {
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    
    if (displayName?.trim()) {
      await updateProfile(userCredential.user, { displayName: displayName.trim() });
    }
    
    await sendEmailVerification(userCredential.user);
    return userCredential.user;
  }

  async logout(): Promise<void> {
    await signOut(auth);
  }

  async getIdToken(): Promise<string> {
    if (!auth.currentUser) throw new Error('No authenticated user');
    return auth.currentUser.getIdToken();
  }

  async updateUserProfile(displayName?: string, photoURL?: string): Promise<void> {
    if (!auth.currentUser) throw new Error('No authenticated user');
    
    const updates: any = {};
    if (displayName) updates.displayName = displayName;
    if (photoURL) updates.photoURL = photoURL;
    
    if (Object.keys(updates).length > 0) {
      await updateProfile(auth.currentUser, updates);
    }
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    const user = auth.currentUser;
    if (!user || !user.email) throw new Error('No authenticated user or email');
    
    const credential = EmailAuthProvider.credential(user.email, currentPassword);
    await reauthenticateWithCredential(user, credential);
    await updatePassword(user, newPassword);
  }

  async resendEmailVerification(): Promise<void> {
    if (!auth.currentUser) throw new Error('No authenticated user');
    await sendEmailVerification(auth.currentUser);
  }

  getCurrentUser(): FirebaseUser | null {
    return auth.currentUser;
  }
}

// Singleton instance
export const firebaseAuth = new FirebaseAuthClient();