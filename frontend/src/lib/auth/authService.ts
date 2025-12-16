// src/lib/auth/authService.ts
import { BaseApi } from '../BaseApi';
import { firebaseAuth } from './firebaseClient';
import { authUser, isAuthenticated, jwtToken, authLoading, userRole } from './authStore';
import type { UserCreateBackend, UserResponseBackend } from './types';
import { mockAuthApi } from './MockAuthApi';
import { AuthApi } from './AuthApi';

// Factory to create API instance
const createAuthApi = () => {
  const useMock = BaseApi.prototype.useMock; // Access BaseApi's useMock
  
  if (useMock) {
    console.log('🔧 Using MockAuthApi for authentication');
    return mockAuthApi;
  }
  
  console.log('🚀 Using real AuthApi for authentication');
  const api = new AuthApi();
  
  // Initialize token from localStorage
  const storedToken = localStorage.getItem('jwt_token');
  if (storedToken) {
    api.setAuthToken(storedToken);
  }
  
  return api;
};

const authApi = createAuthApi();

// Helper to convert snake_case to camelCase for frontend
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

// Helper to convert camelCase to snake_case for backend
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

// Parse JWT to extract user data
function parseJwt(token: string): any {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

// Auth Error Class
export class AuthError extends Error {
  constructor(public code: string, message: string) {
    super(message);
    this.name = 'AuthError';
  }
}

// Token Manager
class TokenManager {
  private refreshAttempted = false;

  async refreshIfNeeded(): Promise<string | null> {
    const currentToken = jwtToken.get();
    if (!currentToken) return null;

    // Check if token is expired
    if (this.isTokenExpired(currentToken)) {
      if (this.refreshAttempted) return null;
      
      this.refreshAttempted = true;
      try {
        console.log('🔄 Attempting token refresh...');
        const newTokens = await authApi.refreshToken();
        const newToken = newTokens.access_token;
        
        // Update token in all places
        jwtToken.set(newToken);
        authApi.setAuthToken(newToken);
        localStorage.setItem('jwt_token', newToken);
        
        console.log('✅ Token refreshed successfully');
        return newToken;
      } catch (error: any) {
        console.error('❌ Token refresh failed:', error.message);
        
        // If refresh is not implemented (501), we should logout
        if (error.message.includes('501') || error.message.includes('not implemented')) {
          console.warn('⚠️ Token refresh not implemented on server, logging out...');
        }
        
        this.clearTokens();
        return null;
      }
    }

    return currentToken;
  }

  private isTokenExpired(token: string): boolean {
    try {
      const payload = parseJwt(token);
      if (!payload || !payload.exp) return true;
      
      const expiryTime = payload.exp * 1000; // Convert to milliseconds
      const currentTime = Date.now();
      const buffer = 60000; // 1 minute buffer
      
      return currentTime >= (expiryTime - buffer);
    } catch {
      return true;
    }
  }

  clearTokens(): void {
    jwtToken.set(null);
    authApi.clearAuthToken();
    localStorage.removeItem('jwt_token');
    this.refreshAttempted = false;
  }
}

const tokenManager = new TokenManager();

// Main Auth Service
export const authService = {
  async login(email: string, password: string): Promise<any> {
    try {
      authLoading.set(true);
      console.log('🔐 Attempting login for:', email);

      // 1. Firebase login
      const firebaseUser = await firebaseAuth.loginWithEmailPassword(email, password);
      console.log('✅ Firebase login successful');
      
      // 2. Get Firebase token
      const firebaseToken = await firebaseUser.getIdToken();
      
      // 3. For mock mode, create a mock token with email
      const tokenToSend = BaseApi.prototype.useMock 
        ? `mock_firebase_token_${email}`
        : firebaseToken;
      
      // 4. Exchange for JWT from backend/mock
      console.log('🔄 Exchanging Firebase token for JWT...');
      const jwtTokens = await authApi.loginWithFirebase(tokenToSend);
      
      // 5. Store JWT in all places
      jwtToken.set(jwtTokens.access_token);
      authApi.setAuthToken(jwtTokens.access_token);
      localStorage.setItem('jwt_token', jwtTokens.access_token);
      console.log('✅ JWT token received and stored');
      
      // 6. Parse JWT to get immediate user data
      const jwtPayload = parseJwt(jwtTokens.access_token);
      if (jwtPayload) {
        const immediateUserData = {
          id: jwtPayload.user_id,
          uid: jwtPayload.uid || firebaseUser.uid,
          email: jwtPayload.email || firebaseUser.email || email,
          displayName: jwtPayload.display_name || firebaseUser.displayName || email.split('@')[0],
          role: jwtPayload.role || 'user',
          emailVerified: jwtPayload.email_verified || firebaseUser.emailVerified || false,
          createdAt: jwtPayload.created_at || new Date().toISOString()
        };
        
        authUser.set(immediateUserData);
        isAuthenticated.set(true);
        console.log('📋 Immediate user data from JWT:', immediateUserData);
      }
      
      // 7. Fetch full user data from backend
      console.log('📋 Fetching complete user data from  ..');
      const backendUserData = await authApi.getCurrentUser();
      
      // 8. Convert snake_case to camelCase for frontend
      const frontendUserData = toCamelCase(backendUserData);
      
      // 9. Update stores with complete data
      authUser.set(frontendUserData);
      isAuthenticated.set(true);
      
      console.log('🎉 Login successful for:', frontendUserData.email);
      return frontendUserData;

    } catch (error: any) {
      console.error('❌ Login failed:', error.message || error);
      this.clearAuthState();
      
      let errorCode = error.code || 'auth/unknown-error';
      let errorMessage = error.message || 'Login failed';
      
      // Handle backend-specific errors
      if (errorMessage.includes('User not registered')) {
        errorCode = 'auth/user-not-registered';
        errorMessage = 'User not registered. Please register first.';
      } else if (errorMessage.includes('Token expired')) {
        errorCode = 'auth/token-expired';
        errorMessage = 'Session expired. Please login again.';
      }
      
      throw new AuthError(errorCode, this.getFriendlyErrorMessage({ code: errorCode, message: errorMessage }));
    } finally {
      authLoading.set(false);
    }
  },

  async register(email: string, password: string, displayName?: string, organizationData?: any): Promise<any> {
    try {
      authLoading.set(true);
      console.log('📝 Attempting registration for:', email);

      // 1. Firebase registration
      const firebaseUser = await firebaseAuth.registerWithEmailPassword(email, password, displayName);
      console.log('✅ Firebase registration successful');
      
      // 2. Get Firebase token
      const firebaseToken = await firebaseUser.getIdToken();
      
      // 3. Prepare backend data in snake_case
      const backendUserData: any = {
        uid: firebaseUser.uid,
        email: email,
        display_name: displayName?.trim() || '',
        role: 'user',
        email_verified: false
      };

      // include org_id when joining an existing organization
      if (organizationData && organizationData.type === 'join' && organizationData.id) {
        backendUserData.org_id = organizationData.id;
      }
      // include org_name when creating a new organization
      if (organizationData && organizationData.type === 'create' && organizationData.name) {
        backendUserData.org_name = organizationData.name;
      }
      
      // 4. Register in backend/mock
      console.log('🔄 Registering user in  ..');
      await authApi.registerUser(backendUserData);
      
      // 5. Auto-login after registration
      const tokenToSend = BaseApi.prototype.useMock 
        ? `mock_firebase_token_${email}`
        : firebaseToken;
      
      console.log('🔄 Auto-login after registration...');
      const jwtTokens = await authApi.loginWithFirebase(tokenToSend);
      
      // 6. Store JWT in all places
      jwtToken.set(jwtTokens.access_token);
      authApi.setAuthToken(jwtTokens.access_token);
      localStorage.setItem('jwt_token', jwtTokens.access_token);
      
      // 7. Parse JWT for immediate data
      const jwtPayload = parseJwt(jwtTokens.access_token);
      if (jwtPayload) {
        const immediateUserData = {
          id: jwtPayload.user_id,
          uid: jwtPayload.uid || firebaseUser.uid,
          email: jwtPayload.email || email,
          displayName: jwtPayload.display_name || displayName || email.split('@')[0],
          role: jwtPayload.role || 'user',
          emailVerified: jwtPayload.email_verified || false,
          createdAt: jwtPayload.created_at || new Date().toISOString()
        };
        
        authUser.set(immediateUserData);
        isAuthenticated.set(true);
      }
      
      // 8. Fetch complete user data
      const backendUser = await authApi.getCurrentUser();
      
      // 9. Convert to camelCase for frontend
      const frontendUserData = toCamelCase(backendUser);
      
      // 10. Update stores with complete data
      authUser.set(frontendUserData);
      isAuthenticated.set(true);
      
      console.log('🎉 Registration successful for:', frontendUserData.email);
      return frontendUserData;

    } catch (error: any) {
      console.error('❌ Registration failed:', error.message || error);
      this.clearAuthState();
      
      // Cleanup Firebase user if backend registration failed
      if (firebaseAuth.getCurrentUser()) {
        try {
          console.log('🧹 Cleaning up Firebase user...');
          await firebaseAuth.logout();
        } catch (cleanupError) {
          console.warn('⚠️ Firebase cleanup failed:', cleanupError);
        }
      }
      
      let errorCode = error.code || 'auth/unknown-error';
      let errorMessage = error.message || 'Registration failed';
      
      // Handle backend-specific errors
      if (errorMessage.includes('User already registered')) {
        errorCode = 'auth/user-exists';
        errorMessage = 'User already registered. Please login instead.';
      } else if (errorMessage.includes('Email already registered')) {
        errorCode = 'auth/email-exists';
        errorMessage = 'Email already registered. Please use a different email.';
      }
      
      throw new AuthError(errorCode, this.getFriendlyErrorMessage({ code: errorCode, message: errorMessage }));
    } finally {
      authLoading.set(false);
    }
  },


  // ========== GOOGLE SIGN-IN ==========
  async loginWithGoogle(firebaseToken: string, organizationId?: string): Promise<any> {
    try {
      authLoading.set(true);
      console.log('🔐 Attempting Google login with organization:', organizationId);

      // Send Google token to backend with organization ID
      const jwtTokens = await authApi.loginWithFirebase(firebaseToken);
      
      // Store JWT in all places
      jwtToken.set(jwtTokens.access_token);
      authApi.setAuthToken(jwtTokens.access_token);
      localStorage.setItem('jwt_token', jwtTokens.access_token);
      console.log('✅ JWT token received and stored');
      
      // Parse JWT to get immediate user data
      const jwtPayload = parseJwt(jwtTokens.access_token);
      if (jwtPayload) {
        const immediateUserData = {
          id: jwtPayload.user_id,
          uid: jwtPayload.uid || 'google_user',
          email: jwtPayload.email || '',
          displayName: jwtPayload.display_name || '',
          role: jwtPayload.role || 'user',
          emailVerified: jwtPayload.email_verified || true,
          createdAt: jwtPayload.created_at || new Date().toISOString()
        };
        
        authUser.set(immediateUserData);
        isAuthenticated.set(true);
        console.log('📋 Immediate user data from JWT:', immediateUserData);
      }
      
      // Fetch complete user data
      console.log('📋 Fetching complete user data from backend...');
      const backendUserData = await authApi.getCurrentUser();
      const frontendUserData = toCamelCase(backendUserData);
      
      // Update stores with complete data
      authUser.set(frontendUserData);
      isAuthenticated.set(true);
      
      console.log('🎉 Google login successful for:', frontendUserData.email);
      return frontendUserData;

    } catch (error: any) {
      console.error('❌ Google login failed:', error.message || error);
      
      // Handle specific backend errors
      if (error.message?.includes('User not registered') || 
          error.message?.includes('404') ||
          error.message?.includes('not found')) {
        throw new AuthError('auth/user-not-registered', 'User not registered. Please complete registration.');
      }
      
      throw new AuthError('auth/google-login-failed', this.getFriendlyErrorMessage(error));
    } finally {
      authLoading.set(false);
    }
  },

    decodeFirebaseToken(token: string): any {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      const decoded = JSON.parse(jsonPayload);
      console.log('🔍 Raw decoded token:', decoded);
      
      // Extract Firebase-specific fields
      return {
        user_id: decoded.user_id,
        sub: decoded.sub,
        uid: decoded.uid || decoded.user_id || decoded.sub,
        email: decoded.email || decoded['firebase']?.identities?.email?.[0],
        email_verified: decoded.email_verified || false,
        name: decoded.name || '',
        picture: decoded.picture || '',
        firebase: decoded.firebase || {}
      };
    } catch (error) {
      console.warn('⚠️ Could not decode Firebase token:', error);
      return {};
    }
  },

  // ========== GOOGLE REGISTRATION ==========
  async registerWithGoogle(firebaseToken: string, displayName: string, organizationData: any): Promise<any> {
    try {
      authLoading.set(true);
      console.log('📝 Attempting Google registration...');

      //const decodedToken = this.decodeFirebaseToken(firebaseToken);
      //console.log('🔍 Decoded Firebase token:', decodedToken);

      // Prepare backend data
      const backendUserData: UserCreateBackend = {
            firebase_token:firebaseToken,
            display_name: displayName,
            organization_data:organizationData
      };
      console.log('🔍 Decoded Firebase token:', backendUserData);
      // Send registration request with Google token
      const response = await authApi.registerUser(backendUserData);
      console.log('✅ Google registration successful in backend');
      // Auto-login after registration
       console.log('🔄 Auto-login after Google registration...');
      const jwtTokens = await authApi.loginWithFirebase(firebaseToken);
      
      // Store JWT in all places
      jwtToken.set(jwtTokens.access_token);
      authApi.setAuthToken(jwtTokens.access_token);
      localStorage.setItem('jwt_token', jwtTokens.access_token);
      
      // Parse JWT for immediate data
      const jwtPayload = parseJwt(jwtTokens.access_token);
      if (jwtPayload) {
        const immediateUserData = {
          id: jwtPayload.user_id,
          uid: jwtPayload.uid || 'google_user',
          email: jwtPayload.email || '',
          displayName: jwtPayload.display_name || displayName,
          role: jwtPayload.role || 'user',
          emailVerified: jwtPayload.email_verified || true,
          createdAt: jwtPayload.created_at || new Date().toISOString()
        };
        
        authUser.set(immediateUserData);
        isAuthenticated.set(true);
      }
      
      // Fetch complete user data
      const backendUser = await authApi.getCurrentUser();
      const frontendUserData = toCamelCase(backendUser);
      
      // Update stores with complete data
      authUser.set(frontendUserData);
      isAuthenticated.set(true);
      
      console.log('🎉 Google registration successful for:', frontendUserData.email);
      return frontendUserData;

    } catch (error: any) {
      console.error('❌ Google registration failed:', error.message || error);
      throw new AuthError('auth/google-registration-failed', this.getFriendlyErrorMessage(error));
    } finally {
      authLoading.set(false);
    }
  },

  // ========== GOOGLE SIGN-IN FLOW (for frontend) ==========
  async handleGoogleSignInFlow(): Promise<{token: string, user: any}> {
    try {
      // Import Firebase dynamically to avoid SSR issues
      const { auth, googleProvider, signInWithPopup } = await import('./firebase');
      
      // Sign in with Google via Firebase
      const result = await signInWithPopup(auth, googleProvider);
      const user = result.user;
      
      // Get Firebase ID token
      const token = await user.getIdToken();
      
      return {
        token,
        user: {
          email: user.email,
          displayName: user.displayName,
          photoURL: user.photoURL,
          emailVerified: user.emailVerified
        }
      };
      
    } catch (error: any) {
      console.error('❌ Google sign-in flow failed:', error);
      
      // Handle specific Google errors
      if (error.code === 'auth/popup-closed-by-user') {
        throw new AuthError('auth/google-cancelled', 'Sign-in was cancelled');
      } else if (error.code === 'auth/popup-blocked') {
        throw new AuthError('auth/popup-blocked', 'Popup blocked. Please allow popups for this site.');
      }
      
      throw new AuthError('auth/google-signin-failed', 'Google sign-in failed. Please try again.');
    }
  },

  async logout(): Promise<void> {
    try {
      console.log('🚪 Logging out...');
      await authApi.logout();
      console.log('✅ Backend logout successful');
    } catch (error: any) {
      console.warn('⚠️ Backend logout failed:', error.message);
    }
    
    try {
      await firebaseAuth.logout();
      console.log('✅ Firebase logout successful');
    } catch (error: any) {
      console.warn('⚠️ Firebase logout failed:', error.message);
    }
    
    this.clearAuthState();
    console.log('👋 User logged out successfully');
  },

  async getCurrentUserProfile(): Promise<any> {
    try {
      console.log('📋 Fetching current user profile...');
      const backendUserData = await authApi.getCurrentUser();
      const frontendUserData = toCamelCase(backendUserData);
      
      // Update store
      authUser.set(frontendUserData);
      return frontendUserData;
    } catch (error: any) {
      console.error('❌ Failed to fetch user profile:', error.message);
      
      // If unauthorized, clear auth state
      if (error.message.includes('401') || error.message.includes('Unauthorized')) {
        this.clearAuthState();
      }
      
      throw new AuthError('fetch-profile-failed', 'Failed to fetch user profile');
    }
  },

  async updateProfile(updates: any): Promise<any> {
    try {
      console.log('✏️ Updating user profile...');
      
      // Convert camelCase to snake_case for backend
      const snakeCaseUpdates = toSnakeCase(updates);
      const backendUserData = await authApi.updateCurrentUserProfile(snakeCaseUpdates);
      
      // Convert back to camelCase for frontend
      const frontendUserData = toCamelCase(backendUserData);
      
      // Update store
      authUser.set(frontendUserData);
      console.log('✅ Profile updated successfully');
      
      return frontendUserData;
    } catch (error: any) {
      console.error('❌ Update profile failed:', error.message);
      throw new AuthError('update-failed', error.message);
    }
  },

  async deleteAccount(): Promise<void> {
    try {
      console.log('🗑️ Deleting user account...');
      await authApi.deleteCurrentUser();
      await this.logout();
      console.log('✅ Account deleted successfully');
    } catch (error: any) {
      console.error('❌ Delete account failed:', error.message);
      throw new AuthError('delete-failed', error.message);
    }
  },

  async getAuthHeaders(): Promise<Record<string, string>> {
    const token = await tokenManager.refreshIfNeeded();
    
    if (!token) {
      console.warn('⚠️ No valid authentication token');
      this.clearAuthState();
      throw new AuthError('auth/no-token', 'Session expired. Please login again.');
    }

    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  },

  async checkAuthStatus(): Promise<boolean> {
    const firebaseUser = firebaseAuth.getCurrentUser();
    const token = jwtToken.get();
    
    if (!firebaseUser || !token) {
      console.log('🔍 No Firebase user or JWT token found');
      this.clearAuthState();
      return false;
    }

    try {
      console.log('🔍 Checking auth status...');
      
      // Check if token is valid/refreshed
      const validToken = await tokenManager.refreshIfNeeded();
      if (!validToken) {
        console.log('❌ Token refresh failed');
        this.clearAuthState();
        return false;
      }
      
      // Verify with backend
      const backendUserData = await authApi.getCurrentUser();
      const frontendUserData = toCamelCase(backendUserData);
      
      // Update stores
      authUser.set(frontendUserData);
      isAuthenticated.set(true);
      
      console.log('✅ Auth status valid for:', frontendUserData.email);
      return true;
      
    } catch (error: any) {
      console.error('❌ Auth status check failed:', error.message);
      this.clearAuthState();
      return false;
    }
  },

  async refreshAuth(): Promise<boolean> {
    try {
      console.log('🔄 Refreshing auth...');
      const token = await tokenManager.refreshIfNeeded();
      if (!token) {
        console.log('❌ No valid token after refresh');
        return false;
      }
      
      const backendUserData = await authApi.getCurrentUser();
      const frontendUserData = toCamelCase(backendUserData);
      
      authUser.set(frontendUserData);
      isAuthenticated.set(true);
      
      console.log('✅ Auth refreshed for:', frontendUserData.email);
      return true;
      
    } catch (error: any) {
      console.error('❌ Auth refresh failed:', error.message);
      return false;
    }
  },

  clearAuthState(): void {
    console.log('🧹 Clearing auth state...');
    authUser.set(null);
    isAuthenticated.set(false);
    jwtToken.set(null);
    tokenManager.clearTokens();
  },

  getFriendlyErrorMessage(error: any): string {
    const map: Record<string, string> = {
      'auth/invalid-email': 'Please enter a valid email address.',
      'auth/user-disabled': 'This account has been disabled.',
      'auth/user-not-found': 'No account found with this email.',
      'auth/user-not-registered': 'User not registered. Please register first.',
      'auth/wrong-password': 'Incorrect password. Please try again.',
      'auth/email-already-in-use': 'An account with this email already exists.',
      'auth/weak-password': 'Password should be at least 6 characters long.',
      'auth/network-request-failed': 'Network error. Please check your connection.',
      'auth/too-many-requests': 'Too many attempts. Please try again later.',
      'auth/requires-recent-login': 'Please login again to perform this action.',
      'auth/user-exists': 'User already registered. Please login instead.',
      'auth/email-exists': 'Email already registered. Please use a different email.',
      'auth/no-token': 'Session expired. Please login again.',
      'auth/token-expired': 'Session expired. Please login again.',
      'auth/google-login-failed': 'Google sign-in failed. Please try again.',
      'auth/google-registration-failed': 'Google registration failed. Please try again.',
      'auth/google-cancelled': 'Google sign-in was cancelled.',
      'auth/popup-blocked': 'Popup blocked. Please allow popups for this site.',
      'auth/user-not-registered': 'User not registered. Please complete registration first.',
      'backend/login-failed': 'Failed to authenticate with server.',
      'backend/registration-failed': 'Failed to register with server.',
      'fetch-profile-failed': 'Failed to load user profile.',
      'update-failed': 'Failed to update profile.',
      'delete-failed': 'Failed to delete account.',
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
  },

  // Get current user from store (in camelCase)
  getCurrentUser(): any {
    let currentUser: any = null;
    authUser.subscribe(value => currentUser = value)();
    return currentUser;
  },

  // Check if user is admin
  isAdmin(): boolean {
    const user = this.getCurrentUser();
    return user?.role === 'admin';
  },

  // Check if user has specific role
  hasRole(role: string): boolean {
    const user = this.getCurrentUser();
    return user?.role === role;
  },

  // Get user role
  getUserRole(): string | null {
    const user = this.getCurrentUser();
    return user?.role || null;
  },

  // Check permissions based on role hierarchy
  hasPermission(requiredPermission: string): boolean {
    const userRole = this.getUserRole();
    if (!userRole) return false;
    
    // Simple role hierarchy
    const roleHierarchy: Record<string, string[]> = {
      'admin': ['admin', 'moderator', 'user', 'viewer'],
      'moderator': ['moderator', 'user', 'viewer'],
      'user': ['user', 'viewer'],
      'viewer': ['viewer']
    };
    
    return roleHierarchy[userRole]?.includes(requiredPermission) || false;
  },

  // Get JWT token
  getToken(): string | null {
    return jwtToken.get();
  },

  // Check if authenticated
  getIsAuthenticated(): boolean {
    let authenticated = false;
    isAuthenticated.subscribe(value => authenticated = value)();
    return authenticated;
  },

  // Health check
  async healthCheck(): Promise<boolean> {
    try {
      const health = await authApi.healthCheck();
      return health.status === 'healthy';
    } catch {
      return false;
    }
  },

  // Initialize auth on app start
  async initialize(): Promise<void> {
    try {
      authLoading.set(true);
      console.log('🔧 Initializing auth service...');
      
      // Check if we have a stored token
      const storedToken = localStorage.getItem('jwt_token');
      if (storedToken) {
        console.log('📁 Found stored JWT token');
        
        // Set token in BaseApi
        authApi.setAuthToken(storedToken);
        jwtToken.set(storedToken);
        
        // Check auth status with backend
        const isAuthenticated = await this.checkAuthStatus();
        
        if (!isAuthenticated) {
          console.log('⚠️ Stored token invalid, clearing auth state');
          this.clearAuthState();
        }
      } else {
        console.log('📭 No stored JWT token found');
        this.clearAuthState();
      }
      
      console.log('✅ Auth service initialized');
    } catch (error) {
      console.error('❌ Auth service initialization failed:', error);
      this.clearAuthState();
    } finally {
      authLoading.set(false);
    }
  }
};

// Initialize auth service on module load
if (typeof window !== 'undefined') {
  // Small delay to let other services initialize
  setTimeout(() => {
    authService.initialize();
  }, 100);
}