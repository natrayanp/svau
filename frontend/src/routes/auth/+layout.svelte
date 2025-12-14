<script>
  import { isAuthenticated } from '$lib/auth/authStore';
  import { authService } from '$lib/auth/authService';
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  
  onMount(() => {
    const unsubscribe = isAuthenticated.subscribe((auth) => {
      // Allow access to auth page for login/register
      const isAuthPage = window.location.pathname === '/auth';
      
      if (!auth && !isAuthPage) {
        goto('/');
      } else if (auth && isAuthPage) {
        // If already authenticated and trying to access auth page, redirect to dashboard
        goto('/auth/dashboard');
      }
    });
    
    return unsubscribe;
  });
</script>

<div class="min-h-screen bg-gray-50">
  <!-- Auth-specific header -->
  <nav class="bg-white shadow-sm">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between h-16">
        <div class="flex items-center space-x-8">
          <a href="/" class="text-xl font-bold text-indigo-600">AuthApp</a>
          {#if $isAuthenticated}
            <div class="flex space-x-4">
              <a href="/auth/dashboard" class="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">Dashboard</a>
              <a href="/auth/profile" class="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">Profile</a>
              <a href="/auth/admin" class="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">Admin</a>
            </div>
          {/if}
        </div>
        <div class="flex items-center">
          {#if $isAuthenticated}
            <button
              on:click={() => authService.logout()}
              class="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
            >
              Logout
            </button>
          {:else}
            <div class="flex space-x-4">
              <a href="/" class="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">Home</a>
            </div>
          {/if}
        </div>
      </div>
    </div>
  </nav>
  
  <main>
    <slot />
  </main>
</div>