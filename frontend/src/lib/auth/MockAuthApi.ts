// src/lib/auth/MockAuthApi.ts
import type { AuthUser, JwtTokens, UserCreateBackend, SuccessResponse } from './types';

export class MockAuthApi {
  private mockUsers: AuthUser[] = [
    {
      id: 1,
      uid: 'mock-uid-1',
      email: 'test@example.com',
      display_name: 'Test User',
      role: 'user',
      email_verified: true,
      created_at: new Date().toISOString()
    },
    {
      id: 2,
      uid: 'mock-uid-2',
      email: 'admin@example.com',
      display_name: 'Admin User',
      role: 'admin',
      email_verified: true,
      created_at: new Date().toISOString()
    }
  ];

  private currentUser: AuthUser | null = this.mockUsers[0];
  private mockJwtToken = 'mock_jwt_token_12345';

  // Simulate network delay
  private delay(ms: number = 300): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async loginWithFirebase(firebaseToken: string): Promise<JwtTokens> {
    await this.delay(500);
    
    // Extract email from mock token
    const email = this.extractEmailFromMockToken(firebaseToken);
    const user = this.mockUsers.find(u => u.email === email);
    
    if (!user) {
      throw new Error('User not registered. Please register first.');
    }

    this.currentUser = user;
    
    return {
      access_token: this.mockJwtToken,
      expires_in: 900 // 15 minutes
    };
  }

  async registerUser(userData: UserCreateBackend): Promise<AuthUser> {
    await this.delay(600);
    
    // Check if user already exists
    const existingUser = this.mockUsers.find(u => u.uid === userData.uid);
    if (existingUser) {
      throw new Error('User already registered');
    }
    
    // Check if email already exists
    const existingEmail = this.mockUsers.find(u => u.email === userData.email);
    if (existingEmail) {
      throw new Error('Email already registered');
    }
    
    const newUser: AuthUser = {
      id: this.mockUsers.length + 1,
      uid: userData.uid,
      email: userData.email,
      display_name: userData.display_name || '',
      role: userData.role || 'user',
      email_verified: userData.email_verified || false,
      created_at: new Date().toISOString()
    };
    
    this.mockUsers.push(newUser);
    this.currentUser = newUser;
    
    return newUser;
  }

  async getCurrentUser(): Promise<AuthUser> {
    await this.delay(300);
    
    if (!this.currentUser) {
      throw new Error('Not authenticated');
    }
    
    return this.currentUser;
  }

  async logout(): Promise<SuccessResponse> {
    await this.delay(200);
    this.currentUser = null;
    
    return {
      success: true,
      message: 'Logged out successfully'
    };
  }

  async refreshToken(): Promise<JwtTokens> {
    await this.delay(400);
    
    if (!this.currentUser) {
      throw new Error('Not authenticated');
    }
    
    return {
      access_token: this.mockJwtToken + '_refreshed',
      expires_in: 900
    };
  }

  async updateCurrentUserProfile(updates: any): Promise<AuthUser> {
    await this.delay(500);
    
    if (!this.currentUser) {
      throw new Error('Not authenticated');
    }
    
    // Update the current user
    this.currentUser = {
      ...this.currentUser,
      ...updates
    };
    
    // Update in mock users array
    const userIndex = this.mockUsers.findIndex(u => u.id === this.currentUser!.id);
    if (userIndex !== -1) {
      this.mockUsers[userIndex] = this.currentUser;
    }
    
    return this.currentUser;
  }

  async deleteCurrentUser(): Promise<SuccessResponse> {
    await this.delay(500);
    
    if (!this.currentUser) {
      throw new Error('Not authenticated');
    }
    
    // Remove from mock users
    this.mockUsers = this.mockUsers.filter(u => u.id !== this.currentUser!.id);
    this.currentUser = null;
    
    return {
      success: true,
      message: 'User account deleted successfully'
    };
  }

  // Helper to extract email from mock Firebase token
  private extractEmailFromMockToken(token: string): string {
    // Simple mock - token format: "mock_firebase_token_email@example.com"
    if (token.includes('mock_firebase_token_')) {
      return token.replace('mock_firebase_token_', '');
    }
    return 'test@example.com'; // default
  }
}

// Singleton instance
export const mockAuthApi = new MockAuthApi();