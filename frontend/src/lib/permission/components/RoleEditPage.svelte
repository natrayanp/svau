<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { 
    permissionStructure, 
    treeSelection, 
    loading,
    permissionActions, 
    selectedPermissionIds, 
    selectedPermissionsAnalysis,
    systemRoles,
    getRoleByKey
  } from '$lib/permission/stores_permission.ts';
  import { PermissionUtils } from '$lib/permission/utils_permission';
  import PermissionTree from '$lib/permission/components/PermissionTree.svelte';

  // Props for different modes
  export let mode = 'view'; // 'new' | 'view' | 'edit'
  export let roleId = $page.params.role || null;

  // Local state
  let roleData = {
    name: '',
    description: '',
    power_level: 0,
    users: 0,
    permissions: []
  };
  
  let originalRoleData = null;
  let saveLoading = false;
  let saveMessage = '';
  let initialized = false;

  // Initialize based on mode
  onMount(() => {
    initializeRoleData();
  });

  async function initializeRoleData() {
    // Ensure permission structure is loaded
    if (!$permissionStructure) {
      await permissionActions.loadPermissionStructure();
    }

    if (mode === 'new') {
      // New mode - start with empty data
      roleData = {
        name: '',
        description: '',
        power_level: 0,
        users: 0,
        permissions: []
      };
      permissionActions.clearAllPermissions();
      initialized = true;
    } else if (roleId) {
      // View or Edit mode - load existing role data FROM STORE
      await loadRoleData();
    }
  }

  async function loadRoleData() {
    try {
      // ENHANCED: Load role data from store instead of API
      const role = getRoleByKey(roleId);
      
      if (!role) {
        saveMessage = '❌ Role not found';
        return;
      }

      // Set role data from store
      roleData = {
        name: role.display_name,
        description: role.description,
        power_level: role.power_level || PermissionUtils.getMaxPower(role.permissions || [], $permissionStructure),
        users: role.user_count || 0,
        permissions: role.permissions || []
      };
      
      // Select permissions in the tree FROM STORE DATA
      permissionActions.clearAllPermissions();
      if (role.permissions && role.permissions.length > 0) {
        role.permissions.forEach(permId => {
          permissionActions.selectPermissionGlobally(permId);
        });
      }
      
      // Store original data for cancel functionality
      originalRoleData = { ...roleData };
      initialized = true;
    } catch (err) {
      console.error('Failed to load role data:', err);
      saveMessage = '❌ Failed to load role data';
    }
  }

  async function saveRole() {
    if (mode === 'view') return;
    
    saveLoading = true;
    saveMessage = '';

    // Validation
    if (mode === 'new' && !roleData.name.trim()) {
      saveMessage = '❌ Role name is required';
      saveLoading = false;
      return;
    }

    try {
      let result;
      const permissionIds = $selectedPermissionIds;
      
      if (mode === 'new') {
        // Create new role
        result = await permissionActions.createRole({
          name: roleData.name,
          description: roleData.description,
          permissions: permissionIds
        });
      } else {
        // Update existing role - STORE WILL BE UPDATED AUTOMATICALLY
        result = await permissionActions.updateRolePermissions(roleId, permissionIds);
      }

      if (result.success) {
        saveMessage = '✅ ' + (mode === 'new' ? 'Role created successfully!' : 'Role updated successfully!');
        
        // Update local role data from store
        const updatedRole = getRoleByKey(mode === 'new' ? result.role.role_key : roleId);
        if (updatedRole) {
          roleData.power_level = updatedRole.power_level || PermissionUtils.getMaxPower(permissionIds, $permissionStructure);
          roleData.permissions = permissionIds;
        }
        
        // Navigate back after successful save
        setTimeout(() => {
          goto('/permission/roles');
        }, 1500);
      } else {
        saveMessage = `❌ ${result.message || 'Failed to save role'}`;
      }
    } catch (error) {
      saveMessage = '❌ Failed to save role';
      console.error('Error saving role:', error);
    } finally {
      saveLoading = false;
    }
  }

  function cancelEdit() {
    if (mode === 'new') {
      // For new mode, just go back
      goto('/permission/roles');
    } else if (originalRoleData) {
      // For edit mode, restore original data and permissions
      roleData = { ...originalRoleData };
      
      // Restore original permissions
      permissionActions.clearAllPermissions();
      originalRoleData.permissions.forEach(permId => {
        permissionActions.selectPermissionGlobally(permId);
      });
      
      // Go back to view mode or navigate away
      if (mode === 'edit') {
        mode = 'view';
      }
    }
  }

  function editRole() {
    mode = 'edit';
  }

  function getHeaderTitle() {
    switch (mode) {
      case 'new':
        return 'Create New Role';
      case 'view':
        return `View Role: ${roleData.name}`;
      case 'edit':
        return `Edit Role: ${roleData.name}`;
      default:
        return 'Role Management';
    }
  }

  function getPowerLevelColor(level) {
    if (level <= 30) return 'from-emerald-500 to-green-400';
    if (level <= 60) return 'from-amber-500 to-yellow-400';
    if (level <= 80) return 'from-orange-500 to-amber-400';
    return 'from-rose-500 to-red-400';
  }

  function getPowerLevelBg(level) {
    if (level <= 30) return 'bg-gradient-to-r from-emerald-100 to-green-100 text-emerald-800';
    if (level <= 60) return 'bg-gradient-to-r from-amber-100 to-yellow-100 text-amber-800';
    if (level <= 80) return 'bg-gradient-to-r from-orange-100 to-amber-100 text-orange-800';
    return 'bg-gradient-to-r from-rose-100 to-red-100 text-rose-800';
  }

  function getActionButtonText() {
    switch (mode) {
      case 'new':
        return 'Create Role';
      case 'edit':
        return 'Save Changes';
      default:
        return 'Save';
    }
  }

  // Update power level when permissions change
  $: if ($permissionStructure && $selectedPermissionIds.length > 0) {
    roleData.power_level = PermissionUtils.getMaxPower($selectedPermissionIds, $permissionStructure);
  }
</script>

<svelte:head>
  <title>{getHeaderTitle()} - Role Management</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 py-8">
  <!--div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8"-->
  <div class="w-full px-4 sm:px-6 lg:px-8">
    <!-- Loading State -->
    {#if $loading.structure || !initialized}
      <div class="flex justify-center items-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        <span class="ml-4 text-gray-600">
          {#if mode === 'new'}
            Initializing new role...
          {:else}
            Loading role data...
          {/if}
        </span>
      </div>
    {:else if !$permissionStructure}
      <div class="premium-card p-6 text-center">
        <div class="text-yellow-800">
          <p class="font-medium">Unable to load permission structure</p>
          <p class="text-sm mt-2">Please check your connection and try again.</p>
          <button 
            on:click={() => permissionActions.loadPermissionStructure()}
            class="mt-4 px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    {:else}
      <!-- Simplified Header -->
      <!--div class="mb-8">
        <div class="premium-card p-6">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-4">
              <a href="/permission/roles" class="text-indigo-600 hover:text-indigo-700 flex items-center space-x-2">
                <span>←</span>
                <span class="font-medium">Back to Roles</span>
              </a>
              <div class="h-8 w-px bg-gray-300"></div>
              <div>
                <h1 class="text-3xl font-bold text-gray-900">
                  {getHeaderTitle()}
                </h1>
                {#if mode === 'view' || mode === 'edit'}
                  <p class="mt-2 text-lg text-gray-600">
                    {roleData.description}
                  </p>
                {/if}
              </div>
            </div>
            {#if mode !== 'new' && roleData.power_level > 0}
              <div class="text-right">
                <div class="text-sm font-medium text-gray-500 mb-2">Power Level</div>
                <div class="flex items-center space-x-3">
                  <div class="relative">
                    <div class="w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                      <span class="text-white font-bold text-lg">{PermissionUtils.getPowerLevelIcon(roleData.power_level)}</span>
                    </div>
                    <div class="absolute -bottom-1 -right-1 w-6 h-6 bg-white rounded-full border-2 border-white shadow-lg flex items-center justify-center">
                      <div class="w-3 h-3 bg-gradient-to-r {getPowerLevelColor(roleData.power_level)} rounded-full"></div>
                    </div>
                  </div>
                  <div>
                    <div class="font-semibold text-gray-900 text-lg">{roleData.power_level}/100</div>
                    <div class="text-sm text-gray-500 capitalize">{PermissionUtils.getPowerLevelLabel(roleData.power_level)}</div>
                  </div>
                </div>
              </div>
            {/if}
          </div>
        </div>
      </div-->

<!-- Role Details and Summary Side by Side - FULL WIDTH -->
<div class="grid grid-cols-1 xl:grid-cols-4 gap-8 mb-8">
  <!-- Role Details Card - Takes 3/4 width -->
  <div class="xl:col-span-3">
    <div class="premium-card h-full">
      <div class="premium-card-header">
        <h2 class="text-xl font-semibold text-gray-900">
          Role Details
          {#if mode === 'view'}
            <span class="ml-2 inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
              View Only
            </span>
          {/if}
        </h2>
      </div>
      <div class="p-6 space-y-4">
        <!-- Role Name -->
        <div>
          <label for="role-name" class="block text-sm font-medium text-gray-700 mb-2">
            Role Name {#if mode === 'new'}<span class="text-red-500">*</span>{/if}
          </label>
          <input
            id="role-name"
            type="text"
            bind:value={roleData.name}
            placeholder="Enter role name"
            class="premium-input {mode === 'view' ? 'bg-gray-100 cursor-not-allowed' : ''}"
            disabled={mode === 'view'}
          />
        </div>

        <!-- Role Description -->
        <div>
          <label for="role-description" class="block text-sm font-medium text-gray-700 mb-2">
            Description
          </label>
          <textarea
            id="role-description"
            bind:value={roleData.description}
            placeholder="Enter role description"
            rows="3"
            class="premium-input {mode === 'view' ? 'bg-gray-100 cursor-not-allowed' : ''}"
            disabled={mode === 'view'}
          ></textarea>
        </div>
      </div>
    </div>
  </div>

  <!-- Summary Card - Takes 1/4 width -->
  <div class="xl:col-span-1">
    <div class="premium-card h-full">
      <div class="premium-card-header">
        <h2 class="text-xl font-semibold text-gray-900">Summary</h2>
      </div>
      <div class="p-6 space-y-4">
        <!-- Selected Permissions Count -->
        <div class="text-center">
          <div class="text-3xl font-bold text-gray-900">{$selectedPermissionIds?.length || 0}</div>
          <div class="text-sm text-gray-500">Selected Permissions</div>
        </div>

        <!-- Power Distribution -->
        {#if $selectedPermissionsAnalysis?.power_distribution}
          <div class="space-y-3">
            <div class="text-sm font-medium text-gray-700">Power Distribution</div>
            <div class="space-y-2">
              <div class="flex items-center justify-between text-sm">
                <div class="flex items-center space-x-2">
                  <div class="w-3 h-3 bg-emerald-500 rounded-full"></div>
                  <span class="text-gray-600">Low</span>
                </div>
                <span class="font-semibold text-gray-900">{$selectedPermissionsAnalysis.power_distribution.low}</span>
              </div>
              <div class="flex items-center justify-between text-sm">
                <div class="flex items-center space-x-2">
                  <div class="w-3 h-3 bg-amber-500 rounded-full"></div>
                  <span class="text-gray-600">Medium</span>
                </div>
                <span class="font-semibold text-gray-900">{$selectedPermissionsAnalysis.power_distribution.medium}</span>
              </div>
              <div class="flex items-center justify-between text-sm">
                <div class="flex items-center space-x-2">
                  <div class="w-3 h-3 bg-orange-500 rounded-full"></div>
                  <span class="text-gray-600">High</span>
                </div>
                <span class="font-semibold text-gray-900">{$selectedPermissionsAnalysis.power_distribution.high}</span>
              </div>
              <div class="flex items-center justify-between text-sm">
                <div class="flex items-center space-x-2">
                  <div class="w-3 h-3 bg-rose-500 rounded-full"></div>
                  <span class="text-gray-600">Critical</span>
                </div>
                <span class="font-semibold text-gray-900">{$selectedPermissionsAnalysis.power_distribution.critical}</span>
              </div>
            </div>
          </div>
        {:else}
          <div class="text-center text-sm text-gray-500 py-4">
            No permissions selected
          </div>
        {/if}
      </div>
    </div>
  </div>
</div>

      <!-- Full Width Permission Tree Card -->
      <div class="premium-card mb-8">
        <div class="premium-card-header">
          <h2 class="text-xl font-semibold text-gray-900">
            Permission Assignment
            {#if mode === 'view'}
              <span class="ml-2 text-sm font-normal text-gray-500">(View Only - Expand/Collapse Enabled)</span>
            {/if}
          </h2>
        </div>
        <div class="p-6">
          <PermissionTree 
            isViewMode={mode === 'view'}
          />
        </div>
      </div>

      <!-- Actions Card -->
      <div class="premium-card">
        <div class="premium-card-header">
          <h2 class="text-xl font-semibold text-gray-900">Actions</h2>
        </div>
        <div class="p-6 space-y-4">
          {#if saveMessage}
            <div class="premium-message {saveMessage.includes('✅') ? 'success' : 'error'}">
              <span class="text-lg">{saveMessage.includes('✅') ? '✅' : '❌'}</span>
              <span class="font-medium">{saveMessage}</span>
            </div>
          {/if}

          <div class="flex flex-col sm:flex-row gap-4">
            {#if mode === 'view'}
              <button
                on:click={editRole}
                class="premium-primary-btn flex-1"
              >
                <span class="text-lg">✏️</span>
                <span>Edit Role</span>
              </button>
              <a
                href="/permission/roles"
                class="premium-secondary-btn flex-1 text-center"
              >
                ← Back to Roles
              </a>
            {:else}
              <button
                on:click={saveRole}
                disabled={saveLoading || (mode === 'new' && !roleData.name.trim())}
                class="premium-primary-btn flex-1 {saveLoading || (mode === 'new' && !roleData.name.trim()) ? 'opacity-50 cursor-not-allowed' : ''}"
              >
                {#if saveLoading}
                  <div class="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
                  <span>Saving...</span>
                {:else}
                  <span class="text-lg">💾</span>
                  <span>{getActionButtonText()}</span>
                {/if}
              </button>
              
              <button
                on:click={cancelEdit}
                class="premium-secondary-btn flex-1 text-center"
              >
                {#if mode === 'new'}
                  Cancel
                {:else}
                  Discard Changes
                {/if}
              </button>
            {/if}
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  /* Premium Card Styles */
  .premium-card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .premium-card:hover {
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    transform: translateY(-1px);
  }

  .premium-card-header {
    border-bottom: 1px solid #e5e7eb;
    padding: 1.5rem 1.5rem 0;
    margin-bottom: 1rem;
  }

  /* Input Styles */
  .premium-input {
    width: 100%;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    background: white;
    transition: all 0.3s ease;
  }

  .premium-input:focus {
    outline: none;
    border-color: #4f46e5;
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
  }

  .premium-input:disabled {
    background: #f9fafb;
    color: #6b7280;
    cursor: not-allowed;
  }

  /* Button Styles */
  .premium-primary-btn {
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
    color: white;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.3s ease;
    box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.3);
    display: flex;
    align-items: center;
    gap: 0.5rem;
    justify-content: center;
  }

  .premium-primary-btn:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 8px 15px -3px rgba(79, 70, 229, 0.4);
  }

  .premium-secondary-btn {
    background: white;
    color: #374151;
    border: 1px solid #d1d5db;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    justify-content: center;
  }

  .premium-secondary-btn:hover {
    background: #f9fafb;
    border-color: #9ca3af;
  }

  /* Message Styles */
  .premium-message {
    padding: 1rem;
    border-radius: 8px;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .premium-message.success {
    background: #ecfdf5;
    color: #065f46;
    border: 1px solid #a7f3d0;
  }

  .premium-message.error {
    background: #fef2f2;
    color: #991b1b;
    border: 1px solid #fca5a5;
  }

  /* Responsive Design */
  @media (max-width: 1280px) {
    .grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 768px) {
    .premium-card-header {
      padding: 1rem 1rem 0;
    }
    
    .p-6 {
      padding: 1rem;
    }
    
    .flex-col {
      flex-direction: column;
    }
    
    .flex-1 {
      flex: 1 1 100%;
    }
  }
</style>