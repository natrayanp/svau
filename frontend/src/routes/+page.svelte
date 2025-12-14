<script>
  import { page } from '$app/stores';
  import { isAuthenticated } from '$lib/auth/authStore';
</script>

<svelte:head>
  <title>Welcome to AuthApp</title>
  <meta name="description" content="A modern authentication app built with Svelte and Firebase" />
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
  <!-- Header -->
  <header class="bg-white shadow-sm">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between items-center h-16">
        <!-- Logo -->
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <h1 class="text-2xl font-bold text-indigo-600">AuthApp</h1>
          </div>
        </div>

        <!-- Navigation - UPDATED TEXT -->
        <nav class="flex items-center space-x-4">
          {#if $isAuthenticated}
            <a 
              href="/auth/dashboard" 
              class="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium transition-colors"
            >
              Dashboard
            </a>
            <a 
              href="/auth/profile" 
              class="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium transition-colors"
            >
              Profile
            </a>
          {:else}
            <!-- UPDATED: Login and Register -->
            <a 
              href="/auth" 
              class="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium transition-colors"
            >
              Login
            </a>
            <a 
              href="/auth" 
              class="bg-indigo-600 text-white hover:bg-indigo-700 px-4 py-2 rounded-md text-sm font-medium transition-colors"
            >
              Register
            </a>
          {/if}
        </nav>
      </div>
    </div>
  </header>

  <!-- Hero Section - UPDATED BUTTON TEXT -->
  <main>
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
      <div class="text-center">
        <h1 class="text-4xl md:text-6xl font-bold text-gray-900 mb-6">
          Welcome to 
          <span class="text-indigo-600">AuthApp</span>
        </h1>
        <p class="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
          A modern, secure authentication system built with Svelte and Firebase. 
          Experience seamless user management and robust security features.
        </p>
        
        <div class="flex flex-col sm:flex-row gap-4 justify-center items-center">
          {#if !$isAuthenticated}
            <!-- UPDATED: Login and Register -->
            <a 
              href="/auth" 
              class="bg-indigo-600 text-white hover:bg-indigo-700 px-8 py-3 rounded-lg text-lg font-semibold transition-colors shadow-lg"
            >
              Get Started Free
            </a>
            <a 
              href="/auth" 
              class="border border-indigo-600 text-indigo-600 hover:bg-indigo-50 px-8 py-3 rounded-lg text-lg font-semibold transition-colors"
            >
              Login
            </a>
          {:else}
            <a 
              href="/auth/dashboard" 
              class="bg-indigo-600 text-white hover:bg-indigo-700 px-8 py-3 rounded-lg text-lg font-semibold transition-colors shadow-lg"
            >
              Go to Dashboard
            </a>
          {/if}
        </div>
      </div>

      <!-- Features Section (unchanged) -->
      <div class="mt-20 grid grid-cols-1 md:grid-cols-3 gap-8">
        <div class="bg-white p-6 rounded-lg shadow-md">
          <div class="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-4">
            <svg class="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <h3 class="text-xl font-semibold text-gray-900 mb-2">Secure Authentication</h3>
          <p class="text-gray-600">
            Enterprise-grade security with Firebase Auth, ensuring your data is always protected.
          </p>
        </div>

        <div class="bg-white p-6 rounded-lg shadow-md">
          <div class="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-4">
            <svg class="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h3 class="text-xl font-semibold text-gray-900 mb-2">Lightning Fast</h3>
          <p class="text-gray-600">
            Built with Svelte for exceptional performance and smooth user experiences.
          </p>
        </div>

        <div class="bg-white p-6 rounded-lg shadow-md">
          <div class="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-4">
            <svg class="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
          <h3 class="text-xl font-semibold text-gray-900 mb-2">User Management</h3>
          <p class="text-gray-600">
            Complete user profile management with role-based access control.
          </p>
        </div>
      </div>
    </div>
  </main>

  <!-- Footer -->
  <footer class="bg-white border-t border-gray-200 mt-16">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div class="text-center text-gray-600">
        <p>&copy; 2024 AuthApp. All rights reserved.</p>
      </div>
    </div>
  </footer>
</div>