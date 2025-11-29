<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import {
    systemRoles,
    users,
    loading,
    permissionActions
  } from '$lib/permission/stores_permission.ts';

  import { PermissionUtils } from '$lib/permission/utils_permission';

  // Export props for customization
  export let showHeader = true;
  //export let compact = false;
  export let enableExport = true;
  export let fullWidth = false;
  export let onViewRole = null; // NEW: View role callback
  export let onEditRole = null; // NEW: Edit role callback
  export let onCreateRole = null; // NEW: Create role callback

  /* ----------------------------------------------------------
     Local UI State
  ----------------------------------------------------------- */
  let searchTerm = '';
  let selectedPowerLevel = 'all';
  let currentPage = 1;
  let pageSize = 10;

  /* ----------------------------------------------------------
     Safe derived data from stores
  ----------------------------------------------------------- */
  $: safeRoles = $systemRoles ?? [];
  $: safeUsers = $users ?? [];

  // Filter roles based on search and power level
  $: filteredRoles = safeRoles.filter(role => {
    const matchesSearch = searchTerm.trim() === '' || 
      (role.display_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (role.description || '').toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesPower = selectedPowerLevel === 'all' || 
      getPowerLevelRange(role.power_level || 0) === selectedPowerLevel;
    
    return matchesSearch && matchesPower;
  });

  $: totalPages = Math.max(1, Math.ceil(filteredRoles.length / pageSize));
  $: paginatedRoles = filteredRoles.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  // Get users count for each role
  $: roleUserCounts = safeRoles.reduce((acc, role) => {
    const usersWithRole = safeUsers.filter(user => 
      Array.isArray(user.roles) && user.roles.includes(role.role_key)
    );
    acc[role.role_key] = usersWithRole.length;
    return acc;
  }, {});

  // Power level filter options
  $: powerLevelOptions = [
    { value: 'all', label: 'All Power Levels' },
    { value: 'low', label: 'Low (1-30)' },
    { value: 'medium', label: 'Medium (31-60)' },
    { value: 'high', label: 'High (61-80)' },
    { value: 'critical', label: 'Critical (81-100)' }
  ];

  /* ----------------------------------------------------------
     Data loading
  ----------------------------------------------------------- */
  onMount(() => {
    // Load roles and users if not already loaded
    if (safeRoles.length === 0) {
      permissionActions.loadSystemRoles();
    }
    if (safeUsers.length === 0) {
      permissionActions.loadUsers();
    }
  });

  /* ----------------------------------------------------------
     Helpers
  ----------------------------------------------------------- */
  const getPowerLevelRange = (power) => {
    if (power <= 30) return 'low';
    if (power <= 60) return 'medium';
    if (power <= 80) return 'high';
    return 'critical';
  };

  const getPowerLevelColor = (power) => {
    const range = getPowerLevelRange(power);
    const colors = {
      low: 'bg-emerald-100 text-emerald-800 border-emerald-200',
      medium: 'bg-amber-100 text-amber-800 border-amber-200',
      high: 'bg-orange-100 text-orange-800 border-orange-200',
      critical: 'bg-rose-100 text-rose-800 border-rose-200'
    };
    return colors[range] || colors.low;
  };

  const getPowerLevelIcon = (power) => {
    if (power <= 30) return '🟢';
    if (power <= 60) return '🟡';
    if (power <= 80) return '🟠';
    return '🔴';
  };

  const goToPage = (page) => {
    if (page >= 1 && page <= totalPages) currentPage = page;
  };

  const changePageSize = (event) => {
    pageSize = parseInt(event.target.value);
    currentPage = 1;
  };

  /* ----------------------------------------------------------
     Role Actions
  ----------------------------------------------------------- */
  const deleteRole = (roleKey, roleName) => {
    if (confirm(`Are you sure you want to delete role "${roleName}"? This action cannot be undone.`)) {
      console.log(`Deleting role ${roleKey}`);
      // permissionActions.deleteRole(roleKey);
    }
  };

  const duplicateRole = (role) => {
    console.log(`Duplicating role ${role.role_key}`);
    // permissionActions.duplicateRole(role);
  };

  /* ----------------------------------------------------------
     CSV Export
  ----------------------------------------------------------- */
  const exportCSV = (filename, rows) => {
    const csv = rows.map(r => r.map(x => `"${x}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
  };

  const exportAllRolesCSV = () => {
    const rows = [
      ["Role Name", "Description", "Power Level", "Users", "Permissions", "System Role"],
      ...safeRoles.map(role => [
        role.display_name ?? '', 
        role.description ?? '', 
        role.power_level ?? 0,
        roleUserCounts[role.role_key] || 0,
        role.permission_count || 0,
        role.is_system_role ? 'Yes' : 'No'
      ])
    ];
    exportCSV("all_roles.csv", rows);
  };

  // Calculate role statistics
  $: roleStats = {
    total: safeRoles.length,
    system: safeRoles.filter(r => r.is_system_role).length,
    custom: safeRoles.filter(r => !r.is_system_role).length,
    highPower: safeRoles.filter(r => (r.power_level || 0) >= 80).length,
    lowUsage: safeRoles.filter(r => (roleUserCounts[r.role_key] || 0) === 0).length
  };
</script>

<!-- Full Width Container -->
<div class="{fullWidth ? 'w-full' : 'min-h-screen bg-gray-50'} {!fullWidth ? 'py-8' : ''}">
  <div class="{fullWidth ? 'w-full' : 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-8'}">
    
    <!-- Header -->
    {#if showHeader}
      <div class="mb-8">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-3xl font-bold text-gray-900">Role Management</h1>
            <p class="mt-2 text-lg text-gray-600">
              Manage system roles and permissions
            </p>
          </div>
          <div class="flex items-center space-x-4">
            <!-- Add New Role Button -->
            {#if onCreateRole}
              <button
                on:click={onCreateRole}
                class="bg-green-600 text-white hover:bg-green-700 px-4 py-2 rounded-lg font-medium transition-colors duration-200 flex items-center space-x-2"
                title="Create New Role"
              >
                <span>➕</span>
                <span>Add New Role</span>
              </button>
            {/if}
          </div>
        </div>
      </div>
    {/if}

    <!-- Loading State -->
    {#if $loading.roles}
      <div class="flex justify-center items-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        <span class="ml-4 text-gray-600">Loading roles...</span>
      </div>
    {:else}

    <!-- Filters -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div class="flex flex-col sm:flex-row sm:items-center space-y-4 sm:space-y-0 sm:space-x-4">
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

          <!-- Power Level Filter -->
          <select
            bind:value={selectedPowerLevel}
            class="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            {#each powerLevelOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>

          <!-- Export Button -->
          {#if enableExport}
            <button
              on:click={exportAllRolesCSV}
              class="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors duration-200 flex items-center space-x-2"
            >
              <span>📥</span>
              <span>Export CSV</span>
            </button>
          {/if}
        </div>

        <div class="text-sm text-gray-500">
          {filteredRoles.length} {filteredRoles.length === 1 ? 'role' : 'roles'} found
        </div>
      </div>
    </div>

    <!-- Roles Table - Full Width -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden w-full">
      <div class="overflow-x-auto w-full">
        <table class="min-w-full divide-y divide-gray-200 w-full">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/4">Role</th>
              <th class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/6">Power Level</th>
              <th class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/6">Users</th>
              <th class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/6">Permissions</th>
              <th class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/6">Type</th>
              <th class="px-4 sm:px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider w-1/6">Actions</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            {#each paginatedRoles as role}
              <tr class="hover:bg-gray-50 transition-colors duration-150">
                <!-- Role Info -->
                <td class="px-4 sm:px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center">
                    <div class="flex-shrink-0 h-10 w-10 bg-indigo-100 rounded-full flex items-center justify-center">
                      <span class="text-indigo-600 font-semibold text-sm">
                        {(role.display_name || 'RR').substring(0, 2).toUpperCase()}
                      </span>
                    </div>
                    <div class="ml-4">
                      <div class="text-sm font-medium text-gray-900">{role.display_name || 'Unknown Role'}</div>
                      <div class="text-sm text-gray-500 truncate max-w-xs">{role.description || 'No description'}</div>
                    </div>
                  </div>
                </td>

                <!-- Power Level -->
                <td class="px-4 sm:px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center space-x-2">
                    <span class="text-lg">{getPowerLevelIcon(role.power_level || 0)}</span>
                    <div>
                      <div class="text-sm font-medium text-gray-900">{role.power_level || 0}/100</div>
                      <div class="text-xs text-gray-500 capitalize">{getPowerLevelRange(role.power_level || 0)}</div>
                    </div>
                  </div>
                </td>

                <!-- Users -->
                <td class="px-4 sm:px-6 py-4 whitespace-nowrap">
                  <div class="text-sm text-gray-900 font-medium">{roleUserCounts[role.role_key] || 0}</div>
                  <div class="text-xs text-gray-500">users</div>
                </td>

                <!-- Permissions -->
                <td class="px-4 sm:px-6 py-4 whitespace-nowrap">
                  <div class="text-sm text-gray-900 font-medium">{role.permission_count || 0}</div>
                  <div class="text-xs text-gray-500">permissions</div>
                </td>

                <!-- Type -->
                <td class="px-4 sm:px-6 py-4 whitespace-nowrap">
                  {#if role.is_system_role}
                    <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 border border-blue-200">
                      System
                    </span>
                  {:else}
                    <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800 border border-gray-200">
                      Custom
                    </span>
                  {/if}
                </td>

                <!-- Actions -->
                <td class="px-4 sm:px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <div class="flex justify-end space-x-2">
                    <!-- View Button -->
                    {#if onViewRole}
                      <button
                        on:click={() => onViewRole(role.role_key)}
                        class="p-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors duration-200"
                        title="View Role Details"
                      >
                        👁️
                      </button>
                    {/if}

                    <!-- Edit Button -->
                    {#if onEditRole}
                      <button
                        on:click={() => onEditRole(role.role_key)}
                        class="p-2 bg-green-50 text-green-600 rounded-lg hover:bg-green-100 transition-colors duration-200"
                        title="Edit Role"
                      >
                        ✏️
                      </button>
                    {/if}

                    <!-- Duplicate Button -->
                    <button
                      on:click={() => duplicateRole(role)}
                      class="p-2 bg-purple-50 text-purple-600 rounded-lg hover:bg-purple-100 transition-colors duration-200"
                      title="Duplicate Role"
                    >
                      📋
                    </button>

                    <!-- Delete Button (disabled for system roles) -->
                    <button
                      on:click={() => deleteRole(role.role_key, role.display_name)}
                      disabled={role.is_system_role}
                      class="p-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors duration-200 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed"
                      title="{role.is_system_role ? 'Cannot delete system role' : 'Delete Role'}"
                    >
                      🗑️
                    </button>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Empty State -->
      {#if filteredRoles.length === 0}
        <div class="text-center py-12 w-full">
          <div class="text-gray-400 text-6xl mb-4">👑</div>
          <h3 class="text-lg font-medium text-gray-900 mb-2">No roles found</h3>
          <p class="text-gray-500">
            {#if searchTerm || selectedPowerLevel !== 'all'}
              Try adjusting your search or filter criteria
            {:else}
              No roles available in the system
            {/if}
          </p>
          {#if onCreateRole && !searchTerm && selectedPowerLevel === 'all'}
            <button
              on:click={onCreateRole}
              class="mt-4 bg-green-600 text-white hover:bg-green-700 px-4 py-2 rounded-lg font-medium transition-colors duration-200 flex items-center space-x-2 mx-auto"
            >
              <span>➕</span>
              <span>Create First Role</span>
            </button>
          {/if}
        </div>
      {/if}
    </div>

    <!-- Pagination -->
    {#if filteredRoles.length > 0}
      <div class="flex flex-col sm:flex-row items-center justify-between gap-4 pt-6 w-full">
        <div class="text-sm text-gray-500 text-center sm:text-left">
          Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, filteredRoles.length)} of {filteredRoles.length} roles
        </div>
        <div class="flex items-center space-x-2">
          <button
            on:click={() => goToPage(currentPage - 1)}
            disabled={currentPage === 1}
            class="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
          >
            Previous
          </button>
          <div class="flex items-center space-x-1">
            {#each Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              let pageNum;
              if (totalPages <= 5) {
                pageNum = i + 1;
              } else if (currentPage <= 3) {
                pageNum = i + 1;
              } else if (currentPage >= totalPages - 2) {
                pageNum = totalPages - 4 + i;
              } else {
                pageNum = currentPage - 2 + i;
              }
              return pageNum;
            }) as pageNum}
              <button
                on:click={() => goToPage(pageNum)}
                class:bg-indigo-600={currentPage === pageNum}
                class:text-white={currentPage === pageNum}
                class="w-10 h-10 rounded-lg text-sm font-medium border transition-colors duration-200"
                class:border-indigo-600={currentPage === pageNum}
                class:border-gray-300={currentPage !== pageNum}
                class:text-gray-700={currentPage !== pageNum}
                class:hover:bg-gray-50={currentPage !== pageNum}
              >
                {pageNum}
              </button>
            {/each}
          </div>
          <button
            on:click={() => goToPage(currentPage + 1)}
            disabled={currentPage === totalPages}
            class="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
          >
            Next
          </button>
        </div>
      </div>
    {/if}

    <!-- Stats Summary -->
    <div class="mt-6 grid grid-cols-1 md:grid-cols-5 gap-6 w-full">
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 text-center">
        <div class="text-2xl font-bold text-gray-900">{roleStats.total}</div>
        <div class="text-sm text-gray-500">Total Roles</div>
      </div>
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 text-center">
        <div class="text-2xl font-bold text-gray-900">{roleStats.system}</div>
        <div class="text-sm text-gray-500">System Roles</div>
      </div>
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 text-center">
        <div class="text-2xl font-bold text-gray-900">{roleStats.custom}</div>
        <div class="text-sm text-gray-500">Custom Roles</div>
      </div>
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 text-center">
        <div class="text-2xl font-bold text-gray-900">{roleStats.highPower}</div>
        <div class="text-sm text-gray-500">High Power</div>
      </div>
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 text-center">
        <div class="text-2xl font-bold text-gray-900">{roleStats.lowUsage}</div>
        <div class="text-sm text-gray-500">Unused Roles</div>
      </div>
    </div>

    {/if}
  </div>
</div>

<style>
  .transition-all {
    transition: all 0.3s ease;
  }
</style>