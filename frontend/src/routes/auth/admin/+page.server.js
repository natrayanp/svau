import { authApi } from '$lib/auth/AuthApi';

export async function load() {
  try {
    const [userData, users] = await Promise.all([
      authApi.getUser('mock-user-id'),
      // Mock users data
      Promise.resolve([
        {
          uid: '1',
          email: 'admin@example.com',
          displayName: 'Admin User',
          role: 'admin'
        },
        {
          uid: '2',
          email: 'user@example.com',
          displayName: 'Regular User',
          role: 'user'
        }
      ])
    ]);
    
    return {
      userData,
      users
    };
  } catch (error) {
    return {
      userData: null,
      users: []
    };
  }
}