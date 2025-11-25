import { authApi } from '$lib/auth/AuthApi';

export async function load({ parent }) {
  // This would normally get the user from the session
  // For demo, we'll use mock data
  try {
    const userData = await authApi.getUser('mock-user-id');
    return {
      userData
    };
  } catch (error) {
    return {
      userData: null
    };
  }
}