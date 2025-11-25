import { authApi } from '$lib/auth/AuthApi';

export async function load() {
  try {
    const [userData, stats] = await Promise.all([
      api.getUser('mock-user-id'),
      Promise.resolve({
        totalUsers: 42,
        activeSessions: 15
      })
    ]);
    
    return {
      userData,
      stats
    };
  } catch (error) {
    return {
      userData: null,
      stats: {}
    };
  }
}