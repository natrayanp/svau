<!-- src/routes/auth/+page.svelte -->
<!-- src/routes/auth/+page.svelte -->
<script>
  import { authService } from '$lib/auth/authService';
  import { authLoading } from '$lib/auth/authStore';
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { firebaseAuth } from '$lib/auth/firebaseClient';

  // Form modes
  let activeTab = 'login'; // 'login' or 'register'
  
  // Login form data
  let loginData = {
    email: '',
    password: '',
    organizationId: ''
  };
  
  // Register form data
  let registerData = {
    email: '',
    password: '',
    displayName: '',
    organizationOption: 'join', // 'join' or 'create'
    organizationId: '', // For joining existing organization
    organizationName: '' // For creating new organization
  };
  
  // State management
  let loginErrors = {};
  let registerErrors = {};
  let loginLoading = false;
  let registerLoading = false;
  let googleLoading = false;
  let showLoginPassword = false;
  let showRegisterPassword = false;
  let successMessage = '';
  let isGoogleRegistration = false;

  onMount(() => {
    // Pre-fill demo credentials for development
    if (import.meta.env.DEV) {
      loginData.email = 'demo@example.com';
      loginData.password = 'demo123';
      loginData.organizationId = 'DEMO123';
    }
  });

  // ========== GOOGLE SIGN-IN HANDLER ==========

  async function handleGoogleSignIn() {
    try {
      googleLoading = true;
      loginErrors = {};
      registerErrors = {};
      successMessage = '';
      
      // 1. Sign in with Google
      const googleUser = await firebaseAuth.signInWithGoogle(true);
      
      // 2. Get Firebase ID token and user info
      const token = await googleUser.getIdToken();
          console.log('✅ Firebase token received:', token ? 'Yes (length: ' + token.length + ')' : 'No');
      const googleUserInfo = await firebaseAuth.getGoogleUserInfo();
      console.log('👤 Google user info:', googleUserInfo);
      
      // 3. Try to login first
      try {
        const result = await authService.loginWithGoogle(token);
        successMessage = 'Successfully signed in with Google!';
        setTimeout(() => goto('/dashboard'), 1000);
        return;
      } catch (loginError) {
        // Login failed - user needs to register
        
        // Show modal and get registration data
        const registrationData = await showOrgIdModal(
          googleUserInfo.email,
          token,
          googleUserInfo
        );
        console.log('Registration data from modal:', registrationData);
        if (!registrationData) {
          throw new Error('Family information is required to register');
        }
        
        // Register immediately
        await authService.registerWithGoogle(
          token,
          googleUserInfo.displayName,
          registrationData
        );
        
        successMessage = 'Account created successfully with Google!';
        console.log('✅ Google registration successful');
        // Auto login after registration
        setTimeout(async () => {
          try {
            const result = await authService.loginWithGoogle(token);
            goto('/dashboard');
          } catch (loginError) {
            // If auto-login fails, switch to login tab
            activeTab = 'login';
            successMessage = 'Account created! Please login.';
          }
        }, 1000);
      }
    } catch (error) {
      console.error('Google sign-in error:', error);
      loginErrors.submit = error.message || 'Google sign-in failed. Please try again.';
    } finally {
      googleLoading = false;
    }
  }

  // Updated modal function (for registration only)
  async function showOrgIdModal(userEmail, googleToken, googleUserInfo) {
    return new Promise((resolve) => {
      const modalHtml = `
        <div id="google-org-modal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div class="bg-white rounded-xl shadow-2xl max-w-md w-full overflow-hidden">
            <!-- Modal Header -->
            <div class="bg-blue-50 px-6 py-4 border-b">
              <div class="flex items-center gap-3">
                <div class="h-10 w-10 bg-blue-100 rounded-full flex items-center justify-center">
                  <svg class="h-5 w-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
                <div>
                  <h3 class="text-lg font-semibold text-gray-900">Family</h3>
                  <p class="text-sm text-gray-600">Welcome, ${userEmail}</p>
                </div>
              </div>
            </div>
            
            <!-- Modal Body -->
            <div class="p-6">
              <p class="text-gray-700 mb-4">
                Choose whether you want to join an existing family or create a new one.
              </p>

              <div class="mb-6 space-y-3">
                <div class="flex items-center gap-3 p-3 border border-gray-300 rounded-lg cursor-pointer hover:bg-blue-50 transition-colors">
                  <input 
                    type="radio" 
                    id="org-join-radio" 
                    name="org-mode" 
                    value="join" 
                    checked 
                    class="h-4 w-4 text-blue-600 border-gray-300"
                  />
                  <label for="org-join-radio" class="flex-1 cursor-pointer">
                    <span class="font-medium text-gray-900">Join Existing</span>
                    <p class="text-sm text-gray-600">Enter your family ID</p>
                  </label>
                </div>

                <div class="flex items-center gap-3 p-3 border border-gray-300 rounded-lg cursor-pointer hover:bg-blue-50 transition-colors">
                  <input 
                    type="radio" 
                    id="org-create-radio" 
                    name="org-mode" 
                    value="create" 
                    class="h-4 w-4 text-blue-600 border-gray-300"
                  />
                  <label for="org-create-radio" class="flex-1 cursor-pointer">
                    <span class="font-medium text-gray-900">Create New</span>
                    <p class="text-sm text-gray-600">Create a new family</p>
                  </label>
                </div>
              </div>

              <div id="org-input-container" class="mb-6">
                <label id="org-input-label" class="block text-sm font-medium text-gray-700 mb-2">Family ID</label>
                <input 
                  id="google-org-input" 
                  type="text" 
                  class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Enter family ID or name"
                  autocomplete="off"
                />
                <p id="org-input-help" class="mt-2 text-xs text-gray-500">Ask your family administrator for the ID, or enter a name to create.</p>
              </div>

              <div class="flex justify-end gap-3">
                <button 
                  id="google-org-cancel"
                  class="px-4 py-2 text-gray-600 hover:text-gray-800 font-medium rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button 
                  id="google-org-continue"
                  class="px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Continue
                </button>
              </div>
            </div>
          </div>
        </div>
      `;
      
      

      // Inject modal
      const modalContainer = document.createElement('div');
      modalContainer.innerHTML = modalHtml;
      document.body.appendChild(modalContainer);

      // Initial mode is join
      let mode = 'join';
      const joinRadio = document.getElementById('org-join-radio');
      const createRadio = document.getElementById('org-create-radio');
      const input = document.getElementById('google-org-input');
      const inputLabel = document.getElementById('org-input-label');
      const inputHelp = document.getElementById('org-input-help');

      function setMode(m) {
        mode = m;
        if (mode === 'join') {
          joinRadio.checked = true;
          inputLabel.textContent = 'Family ID';
          input.placeholder = 'Enter family ID (e.g., FAM123)';
          inputHelp.textContent = 'Ask your family administrator for the ID';
          input.value = '';
          input.focus();
        } else {
          createRadio.checked = true;
          inputLabel.textContent = 'Family Name';
          input.placeholder = 'Enter new family name';
          inputHelp.textContent = 'This will create a new family with this name';
          input.value = '';
          input.focus();
        }
      }

      setTimeout(() => setMode('join'), 10);

      joinRadio.addEventListener('change', () => {
        if (joinRadio.checked) setMode('join');
      });
      createRadio.addEventListener('change', () => {
        if (createRadio.checked) setMode('create');
      });

      // Handle Enter key
      input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          document.getElementById('google-org-continue').click();
        }
      });

      // Handle Continue button
      document.getElementById('google-org-continue').addEventListener('click', () => {
        const val = input.value.trim();
        document.body.removeChild(modalContainer);
        if (!val) {
          resolve(null);
          return;
        }

        console.log('Modal input value:', val);
      // Create organizationData here
      const organizationData = mode === 'join' 
        ? { type: 'join', id: val.toUpperCase() }
        : { type: 'create', name: val };
      console.log('Organization data to return:', organizationData);
      resolve(organizationData);

      });

      // Handle Cancel button
      document.getElementById('google-org-cancel').addEventListener('click', () => {
        document.body.removeChild(modalContainer);
        resolve(null);
      });

      // Handle backdrop click
      modalContainer.addEventListener('click', (e) => {
        if (e.target.id === 'google-org-modal') {
          document.body.removeChild(modalContainer);
          resolve(null);
        }
      });
    });
  }
  // ========== LOGIN FUNCTIONS ==========
  const validateLoginForm = () => {
    const newErrors = {};
    
    // Email validation
    if (!loginData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!authService.validateEmail(loginData.email)) {
      newErrors.email = 'Please enter a valid email address';
    }
    
    // Password validation
    if (!loginData.password) {
      newErrors.password = 'Password is required';
    } else if (loginData.password.length < 1) {
      newErrors.password = 'Password must be at least 1 character';
    }
    
    // Family ID validation (UI label only)
    if (!loginData.organizationId.trim()) {
      newErrors.organizationId = 'Family ID is required';
    } else if (!validateOrganizationIdFormat(loginData.organizationId)) {
      newErrors.organizationId = 'Family ID must be 6-12 uppercase letters/numbers';
    }
    
    loginErrors = newErrors;
    return Object.keys(newErrors).length === 0;
  };

  const handleLogin = async () => {
    if (!validateLoginForm()) return;
    
    loginLoading = true;
    loginErrors = {};
    successMessage = '';
    
    try {
      await authService.login(
        loginData.email, 
        loginData.password, 
        loginData.organizationId.toUpperCase()
      );
      
      // Redirect on successful login
      goto('/dashboard');
      
    } catch (error) {
      console.error('Login error:', error);
      loginErrors.submit = error?.message || 'Invalid credentials. Please try again.';
    } finally {
      loginLoading = false;
    }
  };

  const handleLoginInput = (field, value) => {
    loginData[field] = value;
    
    // Clear field error when user starts typing
    if (loginErrors[field]) {
      const { [field]: removed, ...rest } = loginErrors;
      loginErrors = rest;
    }
    
    // Clear success message
    if (successMessage) {
      successMessage = '';
    }
  };

  // ========== REGISTER FUNCTIONS ==========
  const validateRegisterForm = () => {
    const newErrors = {};
    
    // Email validation
    if (!registerData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!authService.validateEmail(registerData.email)) {
      newErrors.email = 'Please enter a valid email address';
    }
    
    // Password validation (skip for Google registration)
    if (!isGoogleRegistration && !registerData.password) {
      newErrors.password = 'Password is required';
    } else if (!isGoogleRegistration && !authService.validatePassword(registerData.password)) {
      newErrors.password = 'Password must be at least 6 characters';
    }
    
    // Display name validation
    if (!authService.validateDisplayName(registerData.displayName)) {
      newErrors.displayName = 'Display name must be at least 2 characters';
    }
    
    // Family validation (UI label only)
    if (registerData.organizationOption === 'join') {
      if (!registerData.organizationId.trim()) {
        newErrors.organizationId = 'Family ID is required to join';
      }
    } else if (registerData.organizationOption === 'create') {
      if (!registerData.organizationName.trim()) {
        newErrors.organizationName = 'Family name is required';
      } else if (registerData.organizationName.trim().length < 3) {
        newErrors.organizationName = 'Family name must be at least 3 characters';
      } else if (registerData.organizationName.trim().length > 50) {
        newErrors.organizationName = 'Family name must be less than 50 characters';
      }
    }
    
    registerErrors = newErrors;
    return Object.keys(newErrors).length === 0;
  };

  // Accept organization ID as entered (no strict format validation)
  const validateOrganizationIdFormat = (id) => {
    return !!id && id.toString().trim().length > 0;
  };

  const handleRegister = async () => {
    if (!validateRegisterForm()) return;
    console.log('handleRegister called. isGoogleRegistration:', isGoogleRegistration);
    registerLoading = true;
    registerErrors = {};
    successMessage = '';
    
    try {
      const organizationData = registerData.organizationOption === 'join' 
        ? {
            type: 'join',
            id: registerData.organizationId.trim().toUpperCase()
          }
        : {
            type: 'create',
            name: registerData.organizationName.trim()
          };
      
      // Different flow for Google vs email/password registration
      if (isGoogleRegistration) {
        // Get Google token again for registration
        const token = await firebaseAuth.getIdToken();
        console.log('✅ Firebase token for registration:', token ? 'Yes (length: ' + token.length + ')' : 'No');
        console.log(token);
          console.log(registerData.displayName);
          console.log(organizationData);
        await authService.registerWithGoogle(
          token,
          registerData.displayName,
          organizationData
        );
      } else {
        // Normal email/password registration
        await authService.register(
          registerData.email,
          registerData.password,
          registerData.displayName,
          organizationData
        );
      }
      
      // Show success message
      successMessage = isGoogleRegistration 
        ? 'Account created successfully with Google!'
        : 'Account created successfully! You can now login.';
      
      // Clear form
      registerData = {
        email: '',
        password: '',
        displayName: '',
        organizationOption: 'join',
        organizationId: '',
        organizationName: ''
      };
      
      // Reset Google registration flag
      isGoogleRegistration = false;
      
      // Auto-switch to login tab
      setTimeout(() => {
        activeTab = 'login';
        successMessage = '';
      }, 3000);
      
    } catch (error) {
      console.error('Registration error:', error);
      registerErrors.submit = error?.message || 'Registration failed. Please try again.';
    } finally {
      registerLoading = false;
    }
  };

  const handleRegisterInput = (field, value) => {
    registerData[field] = value;
    
    // Clear field error when user starts typing
    if (registerErrors[field]) {
      const { [field]: removed, ...rest } = registerErrors;
      registerErrors = rest;
    }
    
    // Clear success message
    if (successMessage) {
      successMessage = '';
    }
  };

  // ========== SHARED FUNCTIONS ==========
  const togglePasswordVisibility = (type) => {
    if (type === 'login') {
      showLoginPassword = !showLoginPassword;
    } else {
      showRegisterPassword = !showRegisterPassword;
    }
  };

  const handleKeyPress = (event, type) => {
    if (event.key === 'Enter') {
      if (type === 'login') {
        handleLogin();
      } else {
        handleRegister();
      }
    }
  };
</script>


<svelte:head>
  <title>{activeTab === 'login' ? 'Login' : 'Register'} - AuthApp</title>
  <meta name="description" content="{activeTab === 'login' ? 'Login to your AuthApp account' : 'Create a new AuthApp account'}" />
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
      <p class="text-sm text-gray-600">Secure authentication for your organization</p>
    </div>
  </div>

  <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
    <!-- Tab Navigation -->
    <div class="flex mb-8 border-b border-gray-200">
      <button
        on:click={() => {
          activeTab = 'login';
          successMessage = '';
        }}
        class={`flex-1 py-4 text-sm font-medium border-b-2 transition-colors ${
          activeTab === 'login'
            ? 'border-indigo-600 text-indigo-600'
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
        }`}
        disabled={loginLoading || registerLoading || googleLoading}
      >
        Login
      </button>
      <button
        on:click={() => {
          activeTab = 'register';
          successMessage = '';
        }}
        class={`flex-1 py-4 text-sm font-medium border-b-2 transition-colors ${
          activeTab === 'register'
            ? 'border-indigo-600 text-indigo-600'
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
        }`}
        disabled={loginLoading || registerLoading || googleLoading}
      >
        Register
      </button>
    </div>

    <!-- Success Message -->
    {#if successMessage}
      <div class="mb-6 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg flex items-center animate-fade-in">
        <svg class="w-5 h-5 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 0 100-16 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
        </svg>
        {successMessage}
      </div>
    {/if}

    <!-- GOOGLE SIGN-IN BUTTON (Shown on both tabs) -->
    <div class="mb-6">
      <button
        on:click={handleGoogleSignIn}
        disabled={googleLoading || loginLoading || registerLoading}
        class="w-full flex items-center justify-center gap-3 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 font-medium py-3 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {#if googleLoading}
          <svg class="animate-spin h-5 w-5 text-gray-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Signing in with Google...
        {:else}
          <svg class="h-5 w-5" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          Continue with Google
        {/if}
      </button>
      
      <div class="mt-4 flex items-center">
        <div class="flex-grow border-t border-gray-300"></div>
        <span class="flex-shrink mx-4 text-gray-500 text-sm">or continue with email</span>
        <div class="flex-grow border-t border-gray-300"></div>
      </div>
    </div>

    <!-- LOGIN FORM -->
    {#if activeTab === 'login'}
      <div class="bg-white py-8 px-6 shadow-xl sm:rounded-2xl sm:px-10 border border-gray-100">
        <!-- Error Message -->
        {#if loginErrors.submit}
          <div class="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center animate-shake">
            <svg class="w-5 h-5 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 0 100-16 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
            </svg>
            {loginErrors.submit}
          </div>
        {/if}

        <form class="space-y-6" on:submit|preventDefault={handleLogin}>
          <!-- Email Field -->
          <div>
            <label for="login-email" class="block text-sm font-medium text-gray-700 mb-1">
              Email address
            </label>
            <input
              id="login-email"
              type="email"
              autocomplete="email"
              required
              bind:value={loginData.email}
              on:input={(e) => handleLoginInput('email', e.target.value)}
              on:keypress={(e) => handleKeyPress(e, 'login')}
              class="block w-full px-4 py-3 border rounded-lg shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all duration-200 {loginErrors.email ? 'border-red-300' : 'border-gray-300'}"
              placeholder="Enter your email"
              disabled={loginLoading || googleLoading}
            />
            {#if loginErrors.email}
              <p class="mt-1 text-sm text-red-600 animate-fade-in">{loginErrors.email}</p>
            {/if}
          </div>

          <!-- Password Field -->
          <div>
            <label for="login-password" class="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <div class="relative">
              <input
                id="login-password"
                type={showLoginPassword ? 'text' : 'password'}
                autocomplete="current-password"
                required
                bind:value={loginData.password}
                on:input={(e) => handleLoginInput('password', e.target.value)}
                on:keypress={(e) => handleKeyPress(e, 'login')}
                class="block w-full px-4 py-3 pr-12 border rounded-lg shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all duration-200 {loginErrors.password ? 'border-red-300' : 'border-gray-300'}"
                placeholder="Enter your password"
                disabled={loginLoading || googleLoading}
              />
              <button
                type="button"
                on:click={() => togglePasswordVisibility('login')}
                class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 transition-colors"
                disabled={loginLoading || googleLoading}
              >
                <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {#if showLoginPassword}
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  {:else}
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  {/if}
                </svg>
              </button>
            </div>
            {#if loginErrors.password}
              <p class="mt-1 text-sm text-red-600 animate-fade-in">{loginErrors.password}</p>
            {/if}
          </div>

          <!-- Organization ID Field -->
          <div>
            <label for="login-org-id" class="block text-sm font-medium text-gray-700 mb-1">
              Organization ID
            </label>
            <input
              id="login-org-id"
              type="text"
              autocomplete="off"
              required
              bind:value={loginData.organizationId}
              on:input={(e) => {
                // Auto-uppercase
                const value = e.target.value.toUpperCase();
                handleLoginInput('organizationId', value);
              }}
              on:keypress={(e) => handleKeyPress(e, 'login')}
              class="block w-full px-4 py-3 border rounded-lg shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all duration-200 {loginErrors.organizationId ? 'border-red-300' : 'border-gray-300'}"
              placeholder="Enter your organization ID (e.g., ORG123)"
              maxlength="12"
              disabled={loginLoading || googleLoading}
            />
            {#if loginErrors.organizationId}
              <p class="mt-1 text-sm text-red-600 animate-fade-in">{loginErrors.organizationId}</p>
            {/if}
            <p class="mt-1 text-xs text-gray-500">
              Ask your administrator for the Organization ID if you don't have it
            </p>
          </div>

          <!-- Submit Button -->
          <div>
            <button
              type="submit"
              disabled={loginLoading || googleLoading || $authLoading}
              class="w-full flex justify-center items-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
            >
              {#if loginLoading || $authLoading}
                <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Logging in...
              {:else}
                Login with Email
              {/if}
            </button>
          </div>
        </form>

        <!-- Login Help -->
        <div class="mt-6 text-center">
          <p class="text-sm text-gray-600">
            Don't have an account?{' '}
            <button
              on:click={() => {
                activeTab = 'register';
                successMessage = '';
              }}
              class="font-medium text-indigo-600 hover:text-indigo-500 focus:outline-none focus:underline transition-colors duration-200"
              disabled={loginLoading || registerLoading || googleLoading}
            >
              Create one now
            </button>
          </p>
        </div>
      </div>
    {/if}

    <!-- REGISTER FORM -->
    {#if activeTab === 'register'}
      <div class="bg-white py-8 px-6 shadow-xl sm:rounded-2xl sm:px-10 border border-gray-100">
        <!-- Error Message -->
        {#if registerErrors.submit}
          <div class="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center animate-shake">
            <svg class="w-5 h-5 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 0 100-16 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
            </svg>
            {registerErrors.submit}
          </div>
        {/if}

        <!-- Google Registration Notice -->
        {#if isGoogleRegistration}
          <div class="mb-6 bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded-lg flex items-center">
            <svg class="w-5 h-5 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M12.395 2.553a1 1 0 00-1.45-.385c-.345.23-.614.558-.822.88-.214.33-.403.713-.57 1.116-.334.804-.614 1.768-.84 2.734a31.365 31.365 0 00-.613 3.58 2.64 2.64 0 01-.945-1.067c-.328-.68-.398-1.534-.398-2.654A1 1 0 005.05 6.05 6.981 6.981 0 003 11a7 7 0 1011.95-4.95c-.592-.591-.98-.985-1.348-1.467-.363-.476-.724-1.063-1.207-2.03zM12.12 15.12A3 3 0 017 13s.879.5 2.5.5c0-1 .5-4 1.25-4.5.5 1 .786 1.293 1.371 1.879A2.99 2.99 0 0113 13a2.99 2.99 0 01-.879 2.121z" clip-rule="evenodd" />
            </svg>
            <div>
              <p class="font-medium">Google Registration</p>
              <p class="text-sm">Please complete your registration to join this organization.</p>
            </div>
          </div>
        {/if}

        <form class="space-y-6" on:submit|preventDefault={handleRegister}>
          <!-- Display Name Field -->
          <div>
            <label for="register-displayName" class="block text-sm font-medium text-gray-700 mb-1">
              Display Name
            </label>
            <input
              id="register-displayName"
              type="text"
              required
              bind:value={registerData.displayName}
              on:input={(e) => handleRegisterInput('displayName', e.target.value)}
              on:keypress={(e) => handleKeyPress(e, 'register')}
              class="block w-full px-4 py-3 border rounded-lg shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all duration-200 {registerErrors.displayName ? 'border-red-300' : 'border-gray-300'}"
              placeholder="Enter your name"
              disabled={registerLoading || googleLoading}
            />
            {#if registerErrors.displayName}
              <p class="mt-1 text-sm text-red-600 animate-fade-in">{registerErrors.displayName}</p>
            {/if}
          </div>

          <!-- Email Field (disabled for Google registration) -->
          <div>
            <label for="register-email" class="block text-sm font-medium text-gray-700 mb-1">
              Email address
            </label>
            <input
              id="register-email"
              type="email"
              autocomplete="email"
              required
              bind:value={registerData.email}
              on:input={(e) => handleRegisterInput('email', e.target.value)}
              on:keypress={(e) => handleKeyPress(e, 'register')}
              class="block w-full px-4 py-3 border rounded-lg shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all duration-200 {registerErrors.email ? 'border-red-300' : 'border-gray-300'}"
              placeholder="Enter your email"
              disabled={registerLoading || googleLoading || isGoogleRegistration}
            />
            {#if registerErrors.email}
              <p class="mt-1 text-sm text-red-600 animate-fade-in">{registerErrors.email}</p>
            {/if}
          </div>

          <!-- Password Field (hidden for Google registration) -->
          {#if !isGoogleRegistration}
            <div>
              <label for="register-password" class="block text-sm font-medium text-gray-700 mb-1">
                Password
              </label>
              <div class="relative">
                <input
                  id="register-password"
                  type={showRegisterPassword ? 'text' : 'password'}
                  autocomplete="new-password"
                  required
                  bind:value={registerData.password}
                  on:input={(e) => handleRegisterInput('password', e.target.value)}
                  on:keypress={(e) => handleKeyPress(e, 'register')}
                  class="block w-full px-4 py-3 pr-12 border rounded-lg shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all duration-200 {registerErrors.password ? 'border-red-300' : 'border-gray-300'}"
                  placeholder="Create a password"
                  disabled={registerLoading || googleLoading}
                />
                <button
                  type="button"
                  on:click={() => togglePasswordVisibility('register')}
                  class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 transition-colors"
                  disabled={registerLoading || googleLoading}
                >
                  <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    {#if showRegisterPassword}
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    {:else}
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                    {/if}
                  </svg>
                </button>
              </div>
              {#if registerErrors.password}
                <p class="mt-1 text-sm text-red-600 animate-fade-in">{registerErrors.password}</p>
              {/if}
              <p class="mt-1 text-xs text-gray-500">Must be at least 6 characters</p>
            </div>
          {/if}

          <!-- Organization Section -->
          <div class="space-y-4">
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Organization
            </label>
            
            <!-- Organization Option Radio Buttons -->
            <div class="space-y-3 mb-4">
              <div class="flex items-center gap-3 p-3 border border-gray-300 rounded-lg cursor-pointer hover:bg-blue-50 transition-colors">
                <input
                  type="radio"
                  id="org-join"
                  value="join"
                  bind:group={registerData.organizationOption}
                  on:change={() => {
                    if (registerErrors.organizationName) delete registerErrors.organizationName;
                  }}
                  disabled={registerLoading || googleLoading}
                  class="h-4 w-4 text-indigo-600 border-gray-300"
                />
                <label for="org-join" class="flex-1 cursor-pointer">
                  <span class="font-medium text-gray-900">Join Existing</span>
                  <p class="text-sm text-gray-600">Enter your organization ID</p>
                </label>
              </div>

              <div class="flex items-center gap-3 p-3 border border-gray-300 rounded-lg cursor-pointer hover:bg-blue-50 transition-colors">
                <input
                  type="radio"
                  id="org-create"
                  value="create"
                  bind:group={registerData.organizationOption}
                  on:change={() => {
                    if (registerErrors.organizationId) delete registerErrors.organizationId;
                  }}
                  disabled={registerLoading || googleLoading}
                  class="h-4 w-4 text-indigo-600 border-gray-300"
                />
                <label for="org-create" class="flex-1 cursor-pointer">
                  <span class="font-medium text-gray-900">Create New</span>
                  <p class="text-sm text-gray-600">Create a new organization</p>
                </label>
              </div>
            </div>

            <!-- Join Existing Organization -->
            {#if registerData.organizationOption === 'join'}
              <div>
                <label for="register-org-id" class="block text-sm font-medium text-gray-700 mb-1">
                  Organization ID
                </label>
                <input
                  id="register-org-id"
                  type="text"
                  autocomplete="off"
                  required
                  bind:value={registerData.organizationId}
                  on:input={(e) => {
                    // Auto-uppercase
                    const value = e.target.value.toUpperCase();
                    handleRegisterInput('organizationId', value);
                  }}
                  on:keypress={(e) => handleKeyPress(e, 'register')}
                  class="block w-full px-4 py-3 border rounded-lg shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all duration-200 {registerErrors.organizationId ? 'border-red-300' : 'border-gray-300'}"
                  placeholder="Enter organization ID to join"
                  maxlength="12"
                  disabled={registerLoading || googleLoading}
                />
                {#if registerErrors.organizationId}
                  <p class="mt-1 text-sm text-red-600 animate-fade-in">{registerErrors.organizationId}</p>
                {/if}
                <p class="mt-1 text-xs text-gray-500">
                  Ask your organization administrator for the ID
                </p>
              </div>
            {/if}

            <!-- Create New Organization -->
            {#if registerData.organizationOption === 'create'}
              <div>
                <label for="register-org-name" class="block text-sm font-medium text-gray-700 mb-1">
                  Organization Name
                </label>
                <input
                  id="register-org-name"
                  type="text"
                  autocomplete="off"
                  required
                  bind:value={registerData.organizationName}
                  on:input={(e) => handleRegisterInput('organizationName', e.target.value)}
                  on:keypress={(e) => handleKeyPress(e, 'register')}
                  class="block w-full px-4 py-3 border rounded-lg shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all duration-200 {registerErrors.organizationName ? 'border-red-300' : 'border-gray-300'}"
                  placeholder="Enter new organization name"
                  maxlength="50"
                  disabled={registerLoading || googleLoading}
                />
                {#if registerErrors.organizationName}
                  <p class="mt-1 text-sm text-red-600 animate-fade-in">{registerErrors.organizationName}</p>
                {/if}
                <p class="mt-1 text-xs text-gray-500">
                  You will become the administrator of this organization
                </p>
              </div>
            {/if}
          </div>

          <!-- Submit Button -->
          <div>
            <button
              type="submit"
              disabled={registerLoading || googleLoading || $authLoading}
              class="w-full flex justify-center items-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
            >
              {#if registerLoading || $authLoading}
                <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {isGoogleRegistration ? 'Completing registration...' : 'Creating account...'}
              {:else}
                {isGoogleRegistration ? 'Complete Registration' : 'Create Account'}
              {/if}
            </button>
          </div>
        </form>

        <!-- Register Help -->
        <div class="mt-6 text-center">
          <p class="text-sm text-gray-600">
            Already have an account?{' '}
            <button
              on:click={() => {
                activeTab = 'login';
                successMessage = '';
                isGoogleRegistration = false;
              }}
              class="font-medium text-indigo-600 hover:text-indigo-500 focus:outline-none focus:underline transition-colors duration-200"
              disabled={loginLoading || registerLoading || googleLoading}
            >
              Login here
            </button>
          </p>
        </div>
      </div>
    {/if}
  </div>

  <!-- Demo credentials -->
  {#if import.meta.env.DEV && activeTab === 'login'}
    <div class="mt-8 mx-auto w-full max-w-md">
      <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div class="text-sm text-yellow-800 text-center">
          <p class="font-medium mb-2">Demo Credentials:</p>
          <div class="space-y-1 font-mono text-xs">
            <p>Email: demo@example.com</p>
            <p>Password: demo123</p>
            <p>Organization ID: DEMO123</p>
          </div>
        </div>
      </div>
    </div>
  {/if}
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