<script>
  import { onMount } from 'svelte';
  import { permissionStructure, loading, systemRoles, permissionActions } from '$lib/permission/stores_permission.ts';
  import { PermissionUtils } from '$lib/permission/utils_permission';

  let searchTerm = '';
  let filteredRoles = [];

  onMount(() => {
    if ($systemRoles.length === 0) {
      permissionActions.loadSystemRoles();
    }
  });

  function filterRoles() {
    if (!searchTerm.trim()) {
      filteredRoles = $systemRoles.filter(role => role && role.role_id);
      return;
    }

    const term = searchTerm.toLowerCase();
    filteredRoles = $systemRoles.filter(
      role =>
        role &&
        role.role_id &&
        (role.display_name?.toLowerCase().includes(term) ||
         role.description?.toLowerCase().includes(term))
    );
  }

  $: if (searchTerm !== undefined && $systemRoles.length > 0) {
    filterRoles();
  }

  $: if ($systemRoles.length > 0 && filteredRoles.length === 0) {
    filteredRoles = $systemRoles.filter(role => role && role.role_id);
  }
</script>

<svelte:head>

  <title>Role Management - AuthApp</title>
  <meta name="description" content="Manage user roles and permissions" />
</svelte:head>

<div class="min-h-screen bg-gray-50 py-8">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <!-- Header -->
    <div class="mb-8">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-3xl font-bold text-gray-900">Role Management</h1>
          <p class="mt-2 text-lg text-gray-600">
            Create and manage user roles with power-based permissions
          </p>
        </div>
        <div class="flex items-center space-x-4">
          <!-- Search -->
          <div class="relative">
            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <span class="text-gray-400">🔍</span>
            </div>
            <input
              type="text"
              bind:value={searchTerm}
              placeholder="Search roles..."
              class="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 w-64"
            />
          </div>

```
      <!-- Create Role Button -->
      <a
        href="/permission/roles/new"
        class="bg-indigo-600 text-white hover:bg-indigo-700 px-4 py-2 rounded-lg font-medium transition-colors duration-200 flex items-center space-x-2"
      >
        <span>+</span>
        <span>Create Role</span>
      </a>
    </div>
  </div>
</div>

<!-- Loading State -->
{#if $loading.roles}
  <div class="flex justify-center items-center py-12">
    <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
    <span class="ml-4 text-gray-600">Loading roles...</span>
  </div>
{:else if $systemRoles.length === 0}
  <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
    <div class="text-yellow-800">
      <p class="font-medium">No roles found</p>
      <p class="text-sm mt-2">Unable to load system roles. Please try again.</p>
      <button 
        on:click={() => permissionActions.loadSystemRoles()}
        class="mt-4 px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700 transition-colors"
      >
        Retry
      </button>
    </div>
  </div>
{:else}
  <!-- Roles Grid -->
  <div class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
    {#each filteredRoles as role (role.role_id)}
      {#if role && role.role_id}
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow duration-200">
          <!-- Role Header -->
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center space-x-3">
              <div class="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
                <span class="text-indigo-600 font-semibold">🏷️</span>
              </div>
              <div>
                <h3 class="font-semibold text-gray-900 text-lg">{role.display_name}</h3>
                {#if role.is_system_role}
                  <span class="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full">
                    System Role
                  </span>
                {/if}
              </div>
            </div>
            <div class="text-right">
              <div class="text-2xl">{PermissionUtils.getPowerLevelIcon(role.power_level)}</div>
              <div class="text-sm text-gray-500">Power {role.power_level}</div>
            </div>
          </div>

          <!-- Description -->
          <p class="text-gray-600 mb-4 text-sm">{role.description}</p>

          <!-- Stats -->
          <div class="grid grid-cols-2 gap-4 mb-4">
            <div class="text-center">
              <div class="text-2xl font-bold text-gray-900">{role.users}</div>
              <div class="text-xs text-gray-500">Users</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-bold text-gray-900">{role.permissions}</div>
              <div class="text-xs text-gray-500">Permissions</div>
            </div>
          </div>

          <!-- Power Level Bar -->
          <div class="mb-4">
            <div class="flex justify-between text-xs text-gray-500 mb-1">
              <span>Power Level</span>
              <span>{role.power_level}/100</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2">
              <div
                class="h-2 rounded-full {
                  role.power_level <= 30 ? 'bg-green-500' :
                  role.power_level <= 60 ? 'bg-yellow-500' :
                  role.power_level <= 80 ? 'bg-orange-500' : 'bg-red-500'
                }"
                style="width: {role.power_level}%"
              ></div>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex space-x-2">
            <a
              href="/permission/roles/{role.role_id}"
              class="flex-1 bg-indigo-600 text-white hover:bg-indigo-700 py-2 px-3 rounded-lg text-sm font-medium text-center transition-colors duration-200"
            >
              Edit Permissions
            </a>
            <a
              href="/permission/users?role={role.role_id}"
              class="flex-1 bg-gray-100 text-gray-700 hover:bg-gray-200 py-2 px-3 rounded-lg text-sm font-medium text-center transition-colors duration-200"
            >
              Manage Users
            </a>
          </div>
        </div>
      {/if}
    {/each}
  </div>

  <!-- Empty State -->
  {#if filteredRoles.length === 0}
    <div class="text-center py-12">
      <div class="text-gray-400 text-6xl mb-4">🔍</div>
      <h3 class="text-lg font-medium text-gray-900 mb-2">No roles found</h3>
      <p class="text-gray-500 mb-6">Try adjusting your search terms or create a new role.</p>
      <a
        href="/permission/roles/new"
        class="bg-indigo-600 text-white hover:bg-indigo-700 px-6 py-3 rounded-lg font-medium transition-colors duration-200 inline-flex items-center space-x-2"
      >
        <span>+</span>
        <span>Create New Role</span>
      </a>
    </div>
  {/if}
{/if}
```

  </div>
</div>

<style>
  .transition-colors {
    transition: color 0.2s ease, background-color 0.2s ease;
  }
  
  .transition-shadow {
    transition: box-shadow 0.2s ease;
  }
</style>
