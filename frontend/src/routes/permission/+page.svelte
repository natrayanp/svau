<script>
  import { page } from '$app/stores';
  import { isAuthenticated, user } from '$lib/auth/stores';
  import { 
    permissionStructure, 
    loading, 
    userPowerLevel, 
    userMaxPower,
    systemStats,
    quickActions,
    systemRoles,
    permissionActions
  } from '$lib/permission/stores_permission';
  import { PermissionUtils } from '$lib/permission/utils_permission';
  import { onMount } from 'svelte';

  let currentTab = 'overview';
  
  onMount(() => {
    // Ensure all data is loaded
    if (!$systemStats) {
      permissionActions.loadSystemStats();
    }
    if ($quickActions.length === 0) {
      permissionActions.loadQuickActions();
    }
    if ($systemRoles.length === 0) {
      permissionActions.loadSystemRoles();
    }
  });
</script>

<svelte:head>
  <title>Permission Management - AuthApp</title>
  <meta name="description" content="Manage user permissions and role-based access control" />
</svelte:head>

<div class="min-h-screen bg-gray-50 py-8">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <!-- Header -->
    <div class="mb-8">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-3xl font-bold text-gray-900">Permission Management</h1>
          <p class="mt-2 text-lg text-gray-600">
            Manage user roles, permissions, and access control across the system
          </p>
        </div>
        <div class="flex items-center space-x-4">
          <div class="text-right">
            <div class="text-sm text-gray-500">Your Power Level</div>
            <div class="flex items-center space-x-2">
              <span class="text-lg">{PermissionUtils.getPowerLevelIcon($userMaxPower)}</span>
              <span class="font-semibold text-gray-900">{$userPowerLevel}</span>
              <span class="text-sm text-gray-500">({$userMaxPower}/100)</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    {#if $loading.structure || $loading.stats || $loading.quickActions}
      <div class="flex justify-center items-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        <span class="ml-4 text-gray-600">Loading permission system...</span>
      </div>
    {:else if !$permissionStructure}
      <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
        <div class="text-yellow-800">
          <p class="font-medium">Unable to load permission structure</p>
          <p class="text-sm mt-2">Please check your connection and try again.</p>
          <button 
            on:click={() => permissionActions.loadPermissionStructure()}
            class="mt-4 px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    {:else}
      <!-- Quick Stats -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <div class="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <span class="text-2xl">👑</span>
              </div>
            </div>
            <div class="ml-4">
              <div class="text-sm font-medium text-gray-500">Total Roles</div>
              <div class="text-2xl font-bold text-gray-900">
                {$systemStats?.total_roles || $systemRoles.length || 0}
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <div class="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <span class="text-2xl">👥</span>
              </div>
            </div>
            <div class="ml-4">
              <div class="text-sm font-medium text-gray-500">Total Users</div>
              <div class="text-2xl font-bold text-gray-900">
                {$systemStats?.total_users || 0}
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <div class="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <span class="text-2xl">🔐</span>
              </div>
            </div>
            <div class="ml-4">
              <div class="text-sm font-medium text-gray-500">Permissions</div>
              <div class="text-2xl font-bold text-gray-900">
                {$permissionStructure.metadata.total_permissions}
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <div class="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                <span class="text-2xl">📈</span>
              </div>
            </div>
            <div class="ml-4">
              <div class="text-sm font-medium text-gray-500">Recent Activity</div>
              <div class="text-2xl font-bold text-gray-900">
                {$systemStats?.recent_activity || 0}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="mb-8">
        <h2 class="text-xl font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {#each $quickActions as action}
            <a
              href={action.href}
              class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow duration-200 group"
            >
              <div class="flex items-center space-x-4">
                <div class="flex-shrink-0">
                  <span class="text-2xl group-hover:scale-110 transition-transform duration-200">{action.icon}</span>
                </div>
                <div>
                  <div class="font-semibold text-gray-900 group-hover:text-indigo-600 transition-colors duration-200">
                    {action.label}
                  </div>
                  <div class="text-sm text-gray-500 mt-1">{action.description}</div>
                </div>
              </div>
            </a>
          {/each}
        </div>
      </div>

      <!-- System Overview -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <!-- System Roles Overview -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 class="text-xl font-semibold text-gray-900 mb-4">System Roles</h2>
          <div class="space-y-4">
            {#each $systemRoles as role}
              <div class="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors duration-200">
                <div class="flex items-center justify-between mb-2">
                  <span class="font-semibold text-gray-900">{role.name}</span>
                  <span class="text-sm">{PermissionUtils.getPowerLevelIcon(role.power_level)}</span>
                </div>
                <div class="text-gray-600 mb-3 text-sm">{role.description}</div>
                <div class="space-y-1 text-sm text-gray-600">
                  <div>Power: {role.power_level}/100</div>
                  <div>{role.users} users</div>
                  <div>{role.permissions} permissions</div>
                </div>
                <div class="mt-3">
                  <a
                    href="/permission/roles/{role.name.toLowerCase()}"
                    class="text-indigo-600 hover:text-indigo-700 text-sm font-medium"
                  >
                    View Details →
                  </a>
                </div>
              </div>
            {/each}
          </div>
        </div>

        <!-- System Modules Overview -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 class="text-xl font-semibold text-gray-900 mb-4">System Modules</h2>
          <div class="space-y-4">
            {#each $permissionStructure.modules as module}
              <div class="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors duration-200">
                <div class="flex items-center justify-between mb-2">
                  <div class="flex items-center space-x-3">
                    <span class="text-lg">{PermissionUtils.getModuleIcon(module)}</span>
                    <span class="font-semibold text-gray-900">{module.name}</span>
                  </div>
                  <span class="text-sm text-gray-500">{module.menus.length} menus</span>
                </div>
                <div class="text-sm text-gray-600 mb-3">{module.description}</div>
                <div class="flex justify-between text-xs text-gray-500">
                  <span>{module.menus.reduce((acc, menu) => acc + menu.cards.length, 0)} cards</span>
                  <span>
                    {module.menus.reduce((acc, menu) => {
                      const cardPermissions = menu.cards.reduce((cardAcc, card) => cardAcc + card.permissions.length, 0);
                      const menuPermissions = menu.permissions ? menu.permissions.length : 0;
                      return acc + cardPermissions + menuPermissions;
                    }, 0)} permissions
                  </span>
                </div>
              </div>
            {/each}
          </div>
        </div>
      </div>

      <!-- Recent Activity Placeholder -->
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 class="text-xl font-semibold text-gray-900 mb-4">Recent Activity</h2>
        <div class="text-center text-gray-500 py-8">
          <p>Activity monitoring coming soon...</p>
          <p class="text-sm mt-2">Track permission changes and user assignments</p>
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .transition-colors {
    transition: color 0.2s ease, background-color 0.2s ease;
  }
  
  .transition-shadow {
    transition: box-shadow 0.2s ease;
  }
  
  .transition-transform {
    transition: transform 0.2s ease;
  }
</style>