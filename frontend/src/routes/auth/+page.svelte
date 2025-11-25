<script>
  import { authService } from '$lib/auth/auth';
  import { authLoading } from '$lib/auth/stores';
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  
  let isLogin = true;
  let formData = {
    email: '',
    password: '',
    displayName: ''
  };
  let errors = {};
  let isLoading = false;
  let showPassword = false;
  let successMessage = '';

  onMount(() => {
    // Pre-fill demo credentials for development
    if (import.meta.env.DEV) {
      formData.email = 'demo@example.com';
      formData.password = 'demo123';
    }
  });

  const validateField = (field, value) => {
    const fieldErrors = {};
    
    switch (field) {
      case 'email':
        if (!value.trim()) {
          fieldErrors.email = 'Email is required';
        } else if (!authService.validateEmail(value)) {
          fieldErrors.email = 'Please enter a valid email address';
        }
        break;
        
      case 'password':
        if (!value) {
          fieldErrors.password = 'Password is required';
        } else if (!authService.validatePassword(value)) {
          fieldErrors.password = 'Password must be at least 6 characters';
        }
        break;
        
      case 'displayName':
        if (!isLogin && !authService.validateDisplayName(value)) {
          fieldErrors.displayName = 'Display name must be at least 2 characters';
        }
        break;
    }
    
    return fieldErrors;
  };

  const validateForm = () => {
    const newErrors = {};
    
    Object.keys(formData).forEach(field => {
      if (field === 'displayName' && isLogin) return;
      
      const fieldErrors = validateField(field, formData[field]);
      Object.assign(newErrors, fieldErrors);
    });
    
    errors = newErrors;
    return Object.keys(newErrors).length === 0;
  };

  const handleInput = (field, value) => {
    formData[field] = value;
    
    // Clear field error when user starts typing
    if (errors[field]) {
      const { [field]: removed, ...rest } = errors;
      errors = rest;
    }
    
    // Clear success message on any input
    if (successMessage) {
      successMessage = '';
    }
  };

  const toggleMode = () => {
    isLogin = !isLogin;
    errors = {};
    successMessage = '';
    
    // Clear display name when switching to login
    if (isLogin) {
      formData.displayName = '';
    }
  };

  const togglePasswordVisibility = () => {
    showPassword = !showPassword;
  };

  const handleAuth = async () => {
    if (!validateForm()) return;
    
    isLoading = true;
    errors = {};
    successMessage = '';
    
    try {
      if (isLogin) {
        await authService.login(formData.email, formData.password);
      } else {
        await authService.register(formData.email, formData.password, formData.displayName);
        successMessage = 'Account created successfully! Please check your email for verification.';
        
        // Clear form after successful registration
        formData = { email: '', password: '', displayName: '' };
        
        // Auto-switch to login mode after successful registration
        setTimeout(() => {
          isLogin = true;
          successMessage = '';
        }, 3000);
        
        return; // Don't redirect immediately after registration
      }
      
      // Redirect on login
      goto('/auth/dashboard');
      
    } catch (error) {
      console.error('Auth error:', error);
      errors.submit = error.message;
    } finally {
      isLoading = false;
    }
  };

  const handleKeyPress = (event) => {
    if (event.key === 'Enter') {
      handleAuth();
    }
  };
</script>

<svelte:head>
  <title>{isLogin ? 'Login' : 'Register'} - AuthApp</title>
  <meta name="description" content="{isLogin ? 'Login to your AuthApp account' : 'Create a new AuthApp account'}" />
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
  <div class="sm:mx-auto sm:w-full sm:max-w-md">
    <div class="text-center">
      <div class="mx-auto h-12 w-12 bg-indigo-600 rounded-full flex items-center justify-center mb-4">
        <svg class="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
      </div>
      <h1 class="text-3xl font-bold text-gray-900 mb-2">AuthApp</h1>
      <h2 class="text-2xl font-extrabold text-gray-900">
        {isLogin ? 'Welcome back' : 'Create your account'}
      </h2>
      <p class="mt-2 text-sm text-gray-600">
        {isLogin ? "Don't have an account? " : "Already have an account? "}
        <button 
          on:click={toggleMode}
          class="font-medium text-indigo-600 hover:text-indigo-500 focus:outline-none focus:underline transition-colors duration-200"
          disabled={isLoading}
        >
          {isLogin ? 'Register' : 'Login'}
        </button>
      </p>
    </div>
  </div>

  <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
    <div class="bg-white py-8 px-6 shadow-xl sm:rounded-2xl sm:px-10 border border-gray-100">
      <!-- Success Message -->
      {#if successMessage}
        <div class="mb-6 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg flex items-center animate-fade-in">
          <svg class="w-5 h-5 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
          </svg>
          {successMessage}
        </div>
      {/if}

      <!-- Error Message -->
      {#if errors.submit}
        <div class="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center animate-shake">
          <svg class="w-5 h-5 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
          </svg>
          {errors.submit}
        </div>
      {/if}

      <form class="space-y-6" on:submit|preventDefault={handleAuth}>
        <!-- Display Name Field (Register only) -->
        {#if !isLogin}
          <div>
            <label for="displayName" class="block text-sm font-medium text-gray-700 mb-1">
              Display Name
            </label>
            <div class="relative">
              <input
                id="displayName"
                name="displayName"
                type="text"
                required={!isLogin}
                bind:value={formData.displayName}
                on:input={(e) => handleInput('displayName', e.target.value)}
                on:keypress={handleKeyPress}
                class="block w-full px-4 py-3 border rounded-lg shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all duration-200 {errors.displayName ? 'border-red-300' : 'border-gray-300'}"
                placeholder="Enter your display name"
                disabled={isLoading}
              />
            </div>
            {#if errors.displayName}
              <p class="mt-1 text-sm text-red-600 animate-fade-in">{errors.displayName}</p>
            {/if}
          </div>
        {/if}

        <!-- Email Field -->
        <div>
          <label for="email" class="block text-sm font-medium text-gray-700 mb-1">
            Email address
          </label>
          <div class="relative">
            <input
              id="email"
              name="email"
              type="email"
              autocomplete="email"
              required
              bind:value={formData.email}
              on:input={(e) => handleInput('email', e.target.value)}
              on:keypress={handleKeyPress}
              class="block w-full px-4 py-3 border rounded-lg shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all duration-200 {errors.email ? 'border-red-300' : 'border-gray-300'}"
              placeholder="Enter your email"
              disabled={isLoading}
            />
          </div>
          {#if errors.email}
            <p class="mt-1 text-sm text-red-600 animate-fade-in">{errors.email}</p>
          {/if}
        </div>

        <!-- Password Field -->
        <div>
          <label for="password" class="block text-sm font-medium text-gray-700 mb-1">
            Password
          </label>
          <div class="relative">
            <input
              id="password"
              name="password"
              type={showPassword ? 'text' : 'password'}
              autocomplete={isLogin ? 'current-password' : 'new-password'}
              required
              bind:value={formData.password}
              on:input={(e) => handleInput('password', e.target.value)}
              on:keypress={handleKeyPress}
              class="block w-full px-4 py-3 pr-12 border rounded-lg shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all duration-200 {errors.password ? 'border-red-300' : 'border-gray-300'}"
              placeholder={isLogin ? 'Enter your password' : 'Create a password'}
              disabled={isLoading}
            />
            <button
              type="button"
              on:click={togglePasswordVisibility}
              class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 transition-colors"
              disabled={isLoading}
            >
              <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {#if showPassword}
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                {:else}
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                {/if}
              </svg>
            </button>
          </div>
          {#if errors.password}
            <p class="mt-1 text-sm text-red-600 animate-fade-in">{errors.password}</p>
          {/if}
          {#if !isLogin}
            <p class="mt-1 text-xs text-gray-500">Must be at least 6 characters</p>
          {/if}
        </div>

        <!-- Submit Button -->
        <div>
          <button
            type="submit"
            disabled={isLoading || $authLoading}
            class="w-full flex justify-center items-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98]"
          >
            {#if isLoading || $authLoading}
              <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {isLogin ? 'Logging in...' : 'Creating account...'}
            {:else}
              {isLogin ? 'Login' : 'Register'}
            {/if}
          </button>
        </div>
      </form>

      <!-- Demo credentials -->
      {#if import.meta.env.DEV}
        <div class="mt-8 pt-6 border-t border-gray-200">
          <div class="text-xs text-gray-500 text-center">
            <p class="font-medium mb-2 text-gray-700">Demo Credentials:</p>
            <div class="space-y-1">
              <p>Email: <span class="font-mono">demo@example.com</span></p>
              <p>Password: <span class="font-mono">demo123</span></p>
            </div>
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .animate-fade-in {
    animation: fadeIn 0.3s ease-in-out;
  }
  
  .animate-shake {
    animation: shake 0.5s ease-in-out;
  }
  
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
  }
  
  @keyframes shake {
    0%, 100% { transform: translateX(0); }
    25% { transform: translateX(-5px); }
    75% { transform: translateX(5px); }
  }
</style>