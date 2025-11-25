<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';

  let userId = $page.params.userId;
  let userData = null;
  let availableRoles = [];
  let selectedRoles = new Set();
  let saveLoading = false;
  let saveMessage = '';

  // Mock user data
  const userMap = {
    1: {
      id: 1,
      name: 'John Doe',
      email: 'john@example.com',
      current_roles: ['creator', 'user_manager'],
      effective_permissions: 18,
      combined_power_level: 80
    },
    2: {
      id: 2,
      name: 'Jane Smith',
      email: 'jane@example.com', 
      current_roles: ['basic'],
      effective_permissions: 8,
      combined_power_level: 10
    },
    3: {
      id: 3,
      name: 'Admin User',
      email: 'admin@example.com',
      current_roles: ['admin'],
      effective_permissions: 35,
      combined_power_level: 100
    }
  };

  // Available roles with power levels
  const roles = [
    { id: 'basic', name: 'Basic', power: 10, permissions: 8, description: 'View-only access' },
    { id: 'creator', name: 'Creator', power: 30, permissions: 15, description: 'Create and edit content' },
    { id: 'user_manager', name: 'User Manager', power: 80, permissions: 8, description: 'Manage users and permissions' },
    { id: 'admin', name: 'Admin', power: 100, permissions: 12, description: 'Full system access' }
  ];

  onMount(() => {
    userData = userMap[userId] || userMap[1];
    availableRoles = roles;
    
    // Initialize selected roles
    userData.current_roles.forEach(role => selectedRoles.add(role));
  });


  $: selectedRoleDetails = Array.from(selectedRoles).map(roleId => 
  availableRoles.find(role => role.id === roleId)
).filter(Boolean);


  function toggleRole(roleId) {
    if (selectedRoles.has(roleId)) {
      selectedRoles.delete(roleId);
    } else {
      selectedRoles.add(roleId);
    }
  }

  function getPowerLevelIcon(power) {
    if (power <= 30) return '🟢';
    if (power <= 60) return '🟡';
    if (power <= 80) return '🟠';
    return '🔴';
  }

  function calculateCombinedPower() {
    let maxPower = 0;
    selectedRoles.forEach(roleId => {
      const role = roles.find(r => r.id === roleId);
      if (role && role.power > maxPower) {
        maxPower = role.power;
      }
    });
    return maxPower;
  }

  function getRiskAssessment() {
    const power = calculateCombinedPower();
    const roleCount = selectedRoles.size;
    
    if (power >= 100) {
      return {
        level: 'critical',
        message: 'User has administrative access',
        recommendation: 'Monitor all administrative activities'
      };
    } else if (power >= 80) {
      return {
        level: 'high', 
        message: 'User can manage other users',
        recommendation: 'Regular audit of user management activities'
      };
    } else if (power >= 60) {
      return {
        level: 'medium',
        message: 'User has content modification capabilities',
        recommendation: 'Standard monitoring recommended'
      };
    } else {
      return {
        level: 'low',
        message: 'User has basic viewing access',
        recommendation: 'Low risk - normal operations'
      };
    }
  }

  async function saveRoles() {
    saveLoading = true;
    saveMessage = '';
    
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      saveMessage = '✅ User roles updated successfully!';
      
      // Update local data
      userData.current_roles = Array.from(selectedRoles);
      userData.combined_power_level = calculateCombinedPower();
      
    } catch (error) {
      saveMessage = '❌ Failed to update user roles';
    } finally {
      saveLoading = false;
    }
  }

  function getRiskColor(level) {
    return {
      critical: 'red',
      high: 'orange', 
      medium: 'yellow',
      low: 'green'
    }[level];
  }
</script>

<svelte:head>
  <title>User Role Assignment - {userData?.name}</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 py-8">
  <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
    <!-- Header -->
    <div class="mb-8">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-4">
          <a href="/permission/users" class="text-indigo-600 hover:text-indigo-700">
            ← Back to Users
          </a>
          <div>
            <h1 class="text-3xl font-bold text-gray-900">User Role Assignment</h1>
            <p class="mt-2 text-lg text-gray-600">
              {userData?.name} ({userData?.email})
            </p>
          </div>
        </div>
        <div class="text-right">
          <div class="text-sm text-gray-500">Current Power</div>
          <div class="flex items-center space-x-2">
            <span class="text-2xl">{getPowerLevelIcon(userData?.combined_power_level || 0)}</span>
            <span class="font-semibold text-gray-900">{calculateCombinedPower()}/100</span>
          </div>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Role Selection -->
      <div class="lg:col-span-2">
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 class="text-xl font-semibold text-gray-900 mb-4">🎯 Available Roles</h2>
          <p class="text-gray-600 mb-6">Select the roles to assign to this user</p>

          <div class="space-y-3">
            {#each availableRoles as role}
              <div class="border border-gray-200 rounded-lg p-4 {
                selectedRoles.has(role.id) ? 'border-indigo-500 bg-indigo-50' : 'hover:border-gray-300'
              }} transition-colors duration-200">
                <div class="flex items-start space-x-3">
                  <input
                    type="checkbox"
                    checked={selectedRoles.has(role.id)}
                    on:change={() => toggleRole(role.id)}
                    class="mt-1 h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                  />
                  <div class="flex-1">
                    <div class="flex items-center justify-between">
                      <div>
                        <span class="font-semibold text-gray-900">{role.name}</span>
                        {#if selectedRoles.has(role.id)}
                          <span class="ml-2 inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            Selected
                          </span>
                        {/if}
                      </div>
                      <div class="flex items-center space-x-2">
                        <span class="text-lg">{getPowerLevelIcon(role.power)}</span>
                        <span class="text-sm text-gray-500">Power {role.power}</span>
                      </div>
                    </div>
                    <p class="text-sm text-gray-600 mt-1">{role.description}</p>
                    <div class="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                      <span>🔐 {role.permissions} permissions</span>
                    </div>
                  </div>
                </div>
              </div>
            {/each}
          </div>
        </div>
      </div>

      <!-- Summary & Actions -->
      <div class="lg:col-span-1">
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 sticky top-8">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">Assignment Summary</h3>
          
          <!-- Current Selection -->
          <div class="mb-6">
            <div class="text-sm text-gray-600 mb-2">Selected Roles ({selectedRoles.size})</div>
            <div class="space-y-2">
              {#each selectedRoleDetails as role}
                <div class="flex items-center justify-between text-sm">
                  <span class="font-medium">{role.name}</span>
                  <span class="text-gray-500">{getPowerLevelIcon(role.power)}</span>
                </div>
              {/each}
            </div>
          </div>

          <!-- Power Analysis -->
          <div class="mb-6">
            <div class="text-sm text-gray-600 mb-2">Power Analysis</div>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span>Combined Power:</span>
                <span class="font-medium">{calculateCombinedPower()}/100</span>
              </div>
              <div class="flex justify-between">
                <span>Risk Level:</span>
                <span class="font-medium capitalize">{getRiskAssessment().level}</span>
              </div>
            </div>
          </div>

          <!-- Risk Assessment -->
          <div class="mb-6">
            <div class="text-sm text-gray-600 mb-2">⚠️ Risk Assessment</div>
            <div class="bg-{getRiskAssessment().level === 'critical' ? 'red' : getRiskAssessment().level === 'high' ? 'orange' : getRiskAssessment().level === 'medium' ? 'yellow' : 'green'}-50 border border-{getRiskAssessment().level === 'critical' ? 'red' : getRiskAssessment().level === 'high' ? 'orange' : getRiskAssessment().level === 'medium' ? 'yellow' : 'green'}-200 rounded-lg p-3">
              <div class="text-sm text-{getRiskAssessment().level === 'critical' ? 'red' : getRiskAssessment().level === 'high' ? 'orange' : getRiskAssessment().level === 'medium' ? 'yellow' : 'green'}-700">
                <div class="font-medium mb-1">{getRiskAssessment().message}</div>
                <div class="text-xs">{getRiskAssessment().recommendation}</div>
              </div>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="space-y-3">
            <button
              on:click={saveRoles}
              disabled={saveLoading}
              class="w-full bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-indigo-400 py-3 px-4 rounded-lg font-medium transition-colors duration-200 flex items-center justify-center space-x-2"
            >
              {#if saveLoading}
                <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Saving...</span>
              {:else}
                <span>💾 Update User Roles</span>
              {/if}
            </button>
            
            <a
              href="/permission/users"
              class="w-full bg-gray-100 text-gray-700 hover:bg-gray-200 py-3 px-4 rounded-lg font-medium transition-colors duration-200 text-center block"
            >
              Cancel
            </a>
          </div>

          {#if saveMessage}
            <div class="mt-4 text-center text-sm {
              saveMessage.includes('✅') ? 'text-green-600' : 'text-red-600'
            }}">
              {saveMessage}
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>
</div>