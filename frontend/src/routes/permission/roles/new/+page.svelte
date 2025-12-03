<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { permissionState, permissionActions } from '$lib/permission/stores_permission';
  import { PermissionUtils } from '$lib/permission/utils_permission';

  let formData = {
    name: '',
    description: '',
    template: ''
  };
  
  let errors = {};
  let isLoading = false;
  let selectedTemplate = null;

  // Available templates
  const templates = [
    {
      id: 'content_viewer',
      name: 'Content Viewer',
      description: 'View-only access to content',
      permissions: 4,
      power_level: 10,
      icon: '👁️'
    },
    {
      id: 'content_creator', 
      name: 'Content Creator',
      description: 'Create and edit content',
      permissions: 8,
      power_level: 30,
      icon: '✏️'
    },
    {
      id: 'user_manager',
      name: 'User Manager',
      description: 'Manage users and permissions',
      permissions: 5, 
      power_level: 80,
      icon: '👥'
    },
    {
      id: 'system_admin',
      name: 'System Administrator',
      description: 'Full system access',
      permissions: 12,
      power_level: 100,
      icon: '⚙️'
    },
    {
      id: 'custom',
      name: 'Custom',
      description: 'Start from scratch',
      permissions: 0,
      power_level: 0,
      icon: '🎨'
    }
  ];

  onMount(() => {
    permissionActions.loadRoleTemplates();
  });

  function selectTemplate(template) {
    selectedTemplate = template;
    formData.template = template.id;
    
    if (template.id !== 'custom') {
      formData.name = template.name;
      formData.description = template.description;
    } else {
      formData.name = '';
      formData.description = '';
    }
  }

  function validateForm() {
    const newErrors = {};
    
    if (!formData.name.trim()) {
      newErrors.name = 'Role name is required';
    }
    
    if (!formData.description.trim()) {
      newErrors.description = 'Description is required';
    }
    
    if (!formData.template) {
      newErrors.template = 'Please select a template';
    }
    
    errors = newErrors;
    return Object.keys(newErrors).length === 0;
  }

  async function createRole() {
    if (!validateForm()) return;
    
    isLoading = true;
    
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Redirect to role editor
      goto(`/permission/roles/${formData.name.toLowerCase()}`);
    } catch (error) {
      errors.submit = 'Failed to create role';
    } finally {
      isLoading = false;
    }
  }
</script>

<svelte:head>
  <title>Create New Role - AuthApp</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 py-8">
  <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
    <!-- Header -->
    <div class="mb-8">
      <div class="flex items-center space-x-4">
        <a href="/permission/roles" class="text-indigo-600 hover:text-indigo-700">
          ← Back to Roles
        </a>
        <div>
          <h1 class="text-3xl font-bold text-gray-900">Create New Role</h1>
          <p class="mt-2 text-lg text-gray-600">
            Start from a template or create a custom role
          </p>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Template Selection -->
      <div class="lg:col-span-2">
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 class="text-xl font-semibold text-gray-900 mb-4">🎯 Start from Template</h2>
          
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              {#each templates as template}
                <button
                  type="button"
                  class="border-2 rounded-lg p-4 cursor-pointer transition-all duration-200 text-left w-full {
                    selectedTemplate?.id === template.id
                      ? 'border-indigo-500 bg-indigo-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }"
                  on:click={() => selectTemplate(template)}
                  on:keydown={(e) => e.key === 'Enter' || e.key === ' ' ? selectTemplate(template) : null}
                >
                  <div class="flex items-start space-x-3">
                    <div class="flex-shrink-0">
                      <span class="text-2xl">{template.icon}</span>
                    </div>
                    <div class="flex-1">
                      <h3 class="font-semibold text-gray-900">{template.name}</h3>
                      <p class="text-sm text-gray-600 mt-1">{template.description}</p>
                      <div class="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                        <span>🔐 {template.permissions} permissions</span>
                        <span>{PermissionUtils.getPowerLevelIcon(template.power_level)} Power {template.power_level}</span>
                      </div>
                    </div>
                    <div class="flex-shrink-0">
                      {#if selectedTemplate?.id === template.id}
                        <div class="w-5 h-5 bg-indigo-600 rounded-full flex items-center justify-center">
                          <svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                          </svg>
                        </div>
                      {:else}
                        <div class="w-5 h-5 border-2 border-gray-300 rounded-full"></div>
                      {/if}
                    </div>
                  </div>
                </button>
              {/each}
            </div>

          {#if errors.template}
            <p class="text-red-600 text-sm mb-4">{errors.template}</p>
          {/if}

          <!-- Role Details Form -->
          <div class="border-t border-gray-200 pt-6">
            <h3 class="text-lg font-semibold text-gray-900 mb-4">Role Details</h3>
            
            <div class="space-y-4">
              <div>
                <label for="name" class="block text-sm font-medium text-gray-700 mb-1">
                  Role Name
                </label>
                <input
                  id="name"
                  type="text"
                  bind:value={formData.name}
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 {
                    errors.name ? 'border-red-300' : ''
                  }}"
                  placeholder="Enter role name"
                />
                {#if errors.name}
                  <p class="text-red-600 text-sm mt-1">{errors.name}</p>
                {/if}
              </div>

              <div>
                <label for="description" class="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  id="description"
                  bind:value={formData.description}
                  rows="3"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 {
                    errors.description ? 'border-red-300' : ''
                  }}"
                  placeholder="Describe what this role can do"
                ></textarea>
                {#if errors.description}
                  <p class="text-red-600 text-sm mt-1">{errors.description}</p>
                {/if}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Summary & Actions -->
      <div class="lg:col-span-1">
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 sticky top-8">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">Summary</h3>
          
          {#if selectedTemplate}
            <div class="space-y-3 mb-6">
              <div class="flex justify-between">
                <span class="text-gray-600">Template:</span>
                <span class="font-medium">{selectedTemplate.name}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">Permissions:</span>
                <span class="font-medium">{selectedTemplate.permissions}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">Power Level:</span>
                <span class="font-medium flex items-center space-x-1">
                  <span>{PermissionUtils.getPowerLevelIcon(selectedTemplate.power_level)}</span>
                  <span>{PermissionUtils.getPowerLevelLabel(selectedTemplate.power_level)}</span>
                </span>
              </div>
            </div>

            <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
              <div class="flex items-start space-x-2">
                <span class="text-blue-600">💡</span>
                <div class="text-sm text-blue-700">
                  <strong>Based on:</strong> {selectedTemplate.name} template
                  {#if selectedTemplate.permissions > 0}
                    <br>+{selectedTemplate.permissions} permissions
                  {/if}
                </div>
              </div>
            </div>
          {:else}
            <div class="text-gray-500 text-sm text-center py-4">
              Select a template to see details
            </div>
          {/if}

          <!-- Action Buttons -->
          <div class="space-y-3">
            <button
              on:click={createRole}
              disabled={isLoading || !selectedTemplate}
              class="w-full bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-indigo-400 py-3 px-4 rounded-lg font-medium transition-colors duration-200 flex items-center justify-center space-x-2"
            >
              {#if isLoading}
                <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Creating...</span>
              {:else}
                <span>🚀 Continue to Permission Editor</span>
              {/if}
            </button>
            
            <a
              href="/permission/roles"
              class="w-full bg-gray-100 text-gray-700 hover:bg-gray-200 py-3 px-4 rounded-lg font-medium transition-colors duration-200 text-center block"
            >
              Cancel
            </a>
          </div>

          {#if errors.submit}
            <p class="text-red-600 text-sm mt-4 text-center">{errors.submit}</p>
          {/if}
        </div>
      </div>
    </div>
  </div>
</div>