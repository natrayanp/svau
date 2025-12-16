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
  User as FirebaseUser,
  GoogleAuthProvider,
  signInWithPopup,
  signInWithRedirect,
  getRedirectResult

} from 'firebase/auth';
import { auth } from './firebase'; // Your firebase config

const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({
  prompt: 'select_account'
});

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

  // ========== GOOGLE SIGN-IN METHODS ==========
  async signInWithGoogle(popup: boolean = true): Promise<FirebaseUser> {
    try {
      if (popup) {
        // Sign in with popup
        const result = await signInWithPopup(auth, googleProvider);
        return result.user;
      } else {
        // Sign in with redirect (for mobile devices)
        await signInWithRedirect(auth, googleProvider);
        
        // Note: You'll need to handle the redirect result separately
        // Usually in your app initialization or a redirect callback page
        throw new Error('Redirect flow requires separate handling');
      }
    } catch (error: any) {
      console.error('Google sign-in error:', error);
      
      // Handle specific Google errors
      if (error.code === 'auth/popup-closed-by-user') {
        throw new Error('Sign-in cancelled');
      } else if (error.code === 'auth/popup-blocked') {
        throw new Error('Popup blocked. Please allow popups for this site.');
      } else if (error.code === 'auth/unauthorized-domain') {
        throw new Error('This domain is not authorized for Google sign-in.');
      }
      
      throw error;
    }
  }

  async handleRedirectResult(): Promise<FirebaseUser | null> {
    try {
      const result = await getRedirectResult(auth);
      if (result) {
        return result.user;
      }
      return null;
    } catch (error) {
      console.error('Redirect result error:', error);
      return null;
    }
  }

  async getIdTokenFromGoogle(): Promise<string> {
    // This is just an alias for getIdToken() - same method works for Google users
    return this.getIdToken();
  }

  async isGoogleUser(): Promise<boolean> {
    const user = this.getCurrentUser();
    if (!user) return false;
    
    // Check if user signed in with Google
    return user.providerData.some(
      (provider) => provider.providerId === 'google.com'
    );
  }

  async getGoogleUserInfo(): Promise<{
    email: string | null;
    displayName: string | null;
    photoURL: string | null;
    emailVerified: boolean;
  }> {
    const user = this.getCurrentUser();
    if (!user) throw new Error('No authenticated user');
    
    return {
      email: user.email,
      displayName: user.displayName,
      photoURL: user.photoURL,
      emailVerified: user.emailVerified
    };
  }


}

// Singleton instance
export const firebaseAuth = new FirebaseAuthClient();

// Export Google provider for direct use if needed
export { googleProvider };