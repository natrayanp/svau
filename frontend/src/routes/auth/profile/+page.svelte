<script>
  import { authUser } from '$lib/auth/authStore';
  import { authApi } from '$lib/auth/AuthApi';
  
  let currentUser;
  let profile = {
    displayName: '',
    email: ''
  };
  let message = '';
  
  authUser.subscribe(value => {
    currentUser = value;
    if (value) {
      profile.displayName = value.displayName || '';
      profile.email = value.email || '';
    }
  });
  
  async function updateProfile() {
    try {
      await api.updateUser(currentUser.uid, profile);
      message = 'Profile updated successfully!';
    } catch (error) {
      message = 'Error updating profile: ' + error.message;
    }
  }
</script>

<div class="max-w-2xl mx-auto py-6 sm:px-6 lg:px-8">
  <div class="px-4 py-6 sm:px-0">
    <h1 class="text-3xl font-bold text-gray-900 mb-6">Profile Settings</h1>
    
    {#if message}
      <div class="mb-4 p-4 rounded-md {message.includes('Error') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}">
        {message}
      </div>
    {/if}
    
    <div class="bg-white shadow rounded-lg p-6">
      <form on:submit|preventDefault={updateProfile} class="space-y-6">
        <div>
          <label for="displayName" class="block text-sm font-medium text-gray-700">Display Name</label>
          <input
            type="text"
            id="displayName"
            bind:value={profile.displayName}
            class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
        
        <div>
          <label for="email" class="block text-sm font-medium text-gray-700">Email</label>
          <input
            type="email"
            id="email"
            bind:value={profile.email}
            class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
        
        <div>
          <button
            type="submit"
            class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            Update Profile
          </button>
        </div>
      </form>
    </div>
  </div>
</div>