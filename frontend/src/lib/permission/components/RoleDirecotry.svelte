<script lang="ts">
  import { onMount } from 'svelte';
  import { rolesStore } from '$lib/permission/stores/permission_entity_stores';
  import { usePaginationControls, usePageSelection, useMutations, useLookup } from '$lib/common/controls';
  import type { Role } from '$lib/permission/stores/types_permission';

  export let showHeader = true;
  export let enableExport = true;
  export let fullWidth = false;
  export let onViewRole: ((role: Role) => void) | null = null;
  export let onEditRole: ((role: Role) => void) | null = null;
  export let onCreateRole: (() => void) | null = null;

  const { pagination: rolesPagination } = rolesStore;
  const { deleteItem: deleteRoleMut } = useMutations(rolesStore);
  const { addItem: addRoleMutation } = useMutations(rolesStore);
  const { getEntities: getRoleById } = useLookup(rolesStore);

  const { 
    currentPage, 
    pageSize, 
    totalPages, 
    totalItems, 
    goToPage, 
    nextPage, 
    prevPage, 
    setPageSize 
  } = usePaginationControls(rolesStore);

  const {
    selectedIds: selectedRoleIds,
    toggleSelection,
    clearSelection,
    toggleAllPageItems,
    allPageItemsSelected,
    somePageItemsSelected,
    hasSelectedItems
  } = usePageSelection(rolesPagination, 'role_key');

  let searchTerm = '';
  let selectedPowerLevel = 'all';
  let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;
  const SEARCH_DEBOUNCE_MS = 300;

  $: pagedRoles = $rolesPagination?.items ?? [];

  const getPowerLevelRange = (power: number) => {
    if (power <= 30) return 'low';
    if (power <= 60) return 'medium';
    if (power <= 80) return 'high';
    return 'critical';
  };

  const getPowerLevelColor = (power: number) => {
    const range = getPowerLevelRange(power);
    const colors: Record<string, string> = {
      low: 'bg-emerald-100 text-emerald-800 border-emerald-200',
      medium: 'bg-amber-100 text-amber-800 border-amber-200',
      high: 'bg-orange-100 text-orange-800 border-orange-200',
      critical: 'bg-rose-100 text-rose-800 border-rose-200'
    };
    return colors[range] || colors.low;
  };

  const getPowerLevelIcon = (power: number) => {
    if (power <= 30) return '🟢';
    if (power <= 60) return '🟡';
    if (power <= 80) return '🟠';
    return '🔴';
  };

  function applyFilter() {
    const filter: any = {};
    if (searchTerm.trim()) filter.q = searchTerm.trim();
    if (selectedPowerLevel !== 'all') filter.power_level_range = selectedPowerLevel;
    rolesStore.setView($currentPage, $pageSize, { queryFilter: filter });
  }

  function loadRoles(page: number = $currentPage) {
    goToPage(page);
    applyFilter();
  }

  function debouncedSearchInput() {
    if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
      goToPage(1);
      loadRoles(1);
    }, SEARCH_DEBOUNCE_MS);
  }

  function clearFilters() {
    searchTerm = '';
    selectedPowerLevel = 'all';
    loadRoles(1);
  }

  function changePageSizeHandler(event: Event) {
    const newSize = parseInt((event.target as HTMLSelectElement).value) || 10;
    setPageSize(newSize);
    goToPage(1);
    loadRoles(1);
  }

  function toggleAllPageRoles() {
    toggleAllPageItems(pagedRoles);
  }

  const deleteRole = async (roleKey: string | string[], roleName?: string) => {
    const roleArray = Array.isArray(roleKey) ? roleKey : [roleKey];
    if (roleArray.length === 0) return;
    const confirmationText = roleArray.length === 1
      ? `Delete role "${roleName ?? roleArray[0]}"?`
      : `Delete ${roleArray.length} roles?`;
    if (confirm(confirmationText)) {
      deleteRoleMut?.(roleArray);
      loadRoles($currentPage);
    }
  };

  const duplicateRole = async (role: Role) => {
    if (addRoleMutation) {
      await addRoleMutation({
        role_key: `${role.role_key}_copy_${Date.now()}`,
        display_name: `${role.display_name || 'Role'} Copy`,
        description: role.description,
        power_level: role.power_level,
        permission_count: role.permission_count,
        permissions: role.permissions || [],
        is_system_role: false,
        user_count: 0
      } as Partial<Role>);
      loadRoles($currentPage);
    }
  };

  const deleteSelectedRoles = async () => {
    if ($selectedRoleIds.length === 0) return;

    const confirmationText =
      $selectedRoleIds.length === 1
        ? `Delete role "${pagedRoles.find(r => r.role_key === $selectedRoleIds[0])?.display_name ?? $selectedRoleIds[0]}"?`
        : `Delete ${$selectedRoleIds.length} selected roles?`;

    if (confirm(confirmationText)) {
      await deleteRoleMut?.($selectedRoleIds);
      clearSelection();
      loadRoles($currentPage);
    }
  };

  const exportCSV = (filename: string, rows: (string | number)[][]) => {
    const csv = rows.map(r => r.map(x => `"${x}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
  };

  const exportSelectedRolesCSV = () => {
    const selectedRoles = pagedRoles.filter(role => 
      $selectedRoleIds.includes(String(role.role_key))
    );
    const rows = [
      ['Role Name', 'Description', 'Power Level', 'Users', 'Permissions', 'System Role'],
      ...selectedRoles.map(role => [
        role.display_name ?? '',
        role.description ?? '',
        role.power_level ?? 0,
        role.user_count || 0,
        role.permission_count || 0,
        role.is_system_role ? 'Yes' : 'No'
      ])
    ];
    exportCSV('selected_roles.csv', rows);
  };

  const exportAllRolesCSV = () => {
    const rows = [
      ['Role Name', 'Description', 'Power Level', 'Users', 'Permissions', 'System Role'],
      ...pagedRoles.map(role => [
        role.display_name ?? '',
        role.description ?? '',
        role.power_level ?? 0,
        role.user_count || 0,
        role.permission_count || 0,
        role.is_system_role ? 'Yes' : 'No'
      ])
    ];
    exportCSV('all_roles.csv', rows);
  };

  $: roleStats = {
    total: $rolesPagination.total || 0,
    system: pagedRoles.filter(r => r.is_system_role).length,
    custom: pagedRoles.filter(r => !r.is_system_role).length,
    highPower: pagedRoles.filter(r => (r.power_level || 0) >= 80).length,
    lowUsage: pagedRoles.filter(r => (r.user_count || 0) === 0).length
  };

  $: powerLevelOptions = [
    { value: 'all', label: 'All Power Levels' },
    { value: 'low', label: 'Low (1-30)' },
    { value: 'medium', label: 'Medium (31-60)' },
    { value: 'high', label: 'High (61-80)' },
    { value: 'critical', label: 'Critical (81-100)' }
  ];

  $: {
    if (pagedRoles.length > 0) {
      const currentPageKeys = new Set(pagedRoles.map((r: any) => String(r.role_key)));
      selectedRoleIds.set($selectedRoleIds.filter(id => currentPageKeys.has(id)));
    } else {
      clearSelection();
    }
  }

  onMount(() => {
    loadRoles(1);
  });
</script>

<div class="{fullWidth ? 'w-full' : 'min-h-screen bg-gray-50'} {!fullWidth ? 'py-8' : ''}">
  <div class="{fullWidth ? 'w-full' : 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-8'}">
    {#if showHeader}
      <div class="mb-8 flex items-center justify-between">
        <div>
          <h1 class="text-3xl font-bold text-gray-900">Role Management</h1>
          <p class="mt-2 text-lg text-gray-600">Manage system roles and permissions</p>
        </div>
        <div class="flex items-center space-x-4">
          {#if onCreateRole}
            <button on:click={onCreateRole} class="bg-green-600 text-white hover:bg-green-700 px-4 py-2 rounded-lg font-medium flex items-center space-x-2">
              <span>➕</span><span>Add New Role</span>
            </button>
          {/if}
        </div>
      </div>
    {/if}

    <!-- Filters & Export -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div class="flex flex-col sm:flex-row sm:items-center space-y-4 sm:space-y-0 sm:space-x-4">
          <!-- Search -->
          <div class="relative">
            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <span class="text-gray-400">🔍</span>
            </div>
            <input type="text" bind:value={searchTerm} on:input={debouncedSearchInput} placeholder="Search roles..." class="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 w-64" />
          </div>

          <!-- Power Level Filter -->
          <select bind:value={selectedPowerLevel} class="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500">
            {#each powerLevelOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>

          <!-- Clear Filters -->
          {#if searchTerm || selectedPowerLevel !== 'all'}
            <button on:click={clearFilters} class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm font-medium flex items-center space-x-2">
              <span>🗑️</span><span>Clear Filters</span>
            </button>
          {/if}

          <!-- Export CSV -->
          {#if enableExport}
            <button on:click={exportAllRolesCSV} class="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium flex items-center space-x-2">
              <span>📥</span><span>Export CSV</span>
            </button>
          {/if}
        </div>

        <!-- Bulk Delete -->
        {#if $selectedRoleIds.length > 0}
            <div class="flex space-x-3">
              <button
                on:click={deleteSelectedRoles}
                class="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition-colors duration-200 flex items-center space-x-1"
              >
                🗑️ <span>Delete {$selectedRoleIds.length} {$selectedRoleIds.length === 1 ? 'role' : 'roles'}</span>
              </button>
            </div>
        {/if}

        <div class="flex flex-col sm:flex-row items-center gap-4">
          <div class="text-sm text-gray-500">{$rolesPagination.total} {$rolesPagination.total === 1 ? 'role' : 'roles'} found</div>
          {#if onCreateRole}
            <button on:click={onCreateRole} class="bg-green-600 text-white hover:bg-green-700 px-4 py-2 rounded-lg font-medium flex items-center space-x-2">
              <span>➕</span><span>Add New Role</span>
            </button>
          {/if}
        </div>
      </div>
    </div>

    <!-- Stats -->
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

    <!-- Roles Table -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden w-full mt-6">
      <div class="overflow-x-auto w-full">
        <table class="min-w-full divide-y divide-gray-200 w-full">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/12">
                <input type="checkbox" checked={$allPageItemsSelected} indeterminate={$somePageItemsSelected} on:change={toggleAllPageRoles} class="h-4 w-4 rounded border-gray-300" />
              </th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/4">Role</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/6">Power Level</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/6">Users</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/6">Permissions</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/6">Type</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider w-1/6">Actions</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            {#each pagedRoles as role}
              <tr class="hover:bg-gray-50 transition-colors duration-150">
                <!-- Checkbox -->
                <td class="px-4 py-4 whitespace-nowrap">
                  <input type="checkbox" checked={$selectedRoleIds.includes(String(role.role_key))} on:change={() => toggleSelection(role.role_key)} class="h-4 w-4 rounded border-gray-300" />
                </td>

                <!-- Role Info -->
                <td class="px-4 py-4 whitespace-nowrap">
                  <div class="flex items-center">
                    <div class="flex-shrink-0 h-10 w-10 bg-indigo-100 rounded-full flex items-center justify-center">
                      <span class="text-indigo-600 font-semibold text-sm">{(role.display_name || 'RR').substring(0,2).toUpperCase()}</span>
                    </div>
                    <div class="ml-4">
                      <div class="text-sm font-medium text-gray-900">{role.display_name || 'Unknown Role'}</div>
                      <div class="text-sm text-gray-500 truncate max-w-xs">{role.description || 'No description'}</div>
                    </div>
                  </div>
                </td>

                <!-- Power Level -->
                <td class="px-4 py-4 whitespace-nowrap">
                  <div class="flex items-center space-x-2">
                    <span class="text-lg">{getPowerLevelIcon(role.power_level || 0)}</span>
                    <div>
                      <div class="text-sm font-medium text-gray-900">{role.power_level || 0}/100</div>
                      <div class="text-xs text-gray-500 capitalize">{getPowerLevelRange(role.power_level || 0)}</div>
                    </div>
                  </div>
                </td>

                <!-- Users -->
                <td class="px-4 py-4 whitespace-nowrap">
                  <div class="text-sm text-gray-900 font-medium">{role.user_count || 0}</div>
                  <div class="text-xs text-gray-500">users</div>
                </td>

                <!-- Permissions -->
                <td class="px-4 py-4 whitespace-nowrap">
                  <div class="text-sm text-gray-900 font-medium">{role.permission_count || 0}</div>
                  <div class="text-xs text-gray-500">permissions</div>
                </td>

                <!-- Type -->
                <td class="px-4 py-4 whitespace-nowrap">
                  {#if role.is_system_role}
                    <span class="inline-flex px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 border border-blue-200">System</span>
                  {:else}
                    <span class="inline-flex px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800 border border-gray-200">Custom</span>
                  {/if}
                </td>

                <!-- Actions -->
                <td class="px-4 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <div class="flex justify-end space-x-2">
                    {#if onViewRole}<button on:click={() => onViewRole(role)} class="p-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors" title="View Role Details">👁️</button>{/if}
                    {#if onEditRole}<button on:click={() => onEditRole(role)} class="p-2 bg-green-50 text-green-600 rounded-lg hover:bg-green-100 transition-colors" title="Edit Role">✏️</button>{/if}
                    <button on:click={() => duplicateRole(role)} class="p-2 bg-purple-50 text-purple-600 rounded-lg hover:bg-purple-100 transition-colors" title="Duplicate Role">📋</button>
                    <button on:click={() => deleteRole(role.role_key, role.display_name)} disabled={role.is_system_role} class="p-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed" title={role.is_system_role ? 'Cannot delete system role' : 'Delete Role'}>🗑️</button>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      {#if $rolesPagination.total === 0}
        <div class="text-center py-12 w-full">
          <div class="text-gray-400 text-6xl mb-4">👑</div>
          <h3 class="text-lg font-medium text-gray-900 mb-2">No roles found</h3>
          <p class="text-gray-500">{#if searchTerm || selectedPowerLevel !== 'all'}Try adjusting your search or filter criteria{:else}No roles available in the system{/if}</p>
          {#if onCreateRole && !searchTerm && selectedPowerLevel === 'all'}
            <button on:click={onCreateRole} class="mt-4 bg-green-600 text-white hover:bg-green-700 px-4 py-2 rounded-lg font-medium flex items-center space-x-2 mx-auto"><span>➕</span><span>Create First Role</span></button>
          {/if}
        </div>
      {/if}
    </div>

    <!-- Pagination -->
    {#if $rolesPagination.total > 0}
      <div class="flex flex-col sm:flex-row items-center justify-between gap-4 pt-6 w-full">
        <div class="text-sm text-gray-500 text-center sm:text-left">
          Showing {(($currentPage - 1) * $pageSize + 1)} to {Math.min($currentPage * $pageSize, $totalItems)} of {$totalItems} roles
        </div>
        <div class="flex items-center space-x-2">
          <button on:click={prevPage} disabled={$currentPage === 1} class="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200">Previous</button>
          <div class="flex items-center space-x-1">
            {#each Array.from({ length: Math.min(5, $totalPages) }, (_, i) => {
              let pageNum;
              if ($totalPages <= 5) pageNum = i + 1;
              else if ($currentPage <= 3) pageNum = i + 1;
              else if ($currentPage >= $totalPages - 2) pageNum = $totalPages - 4 + i;
              else pageNum = $currentPage - 2 + i;
              return pageNum;
            }) as pageNum}
              <button on:click={() => goToPage(pageNum)} class="w-10 h-10 rounded-lg text-sm font-medium border transition-colors duration-200"
                class:bg-indigo-600={$currentPage === pageNum} class:text-white={$currentPage === pageNum}
                class:border-indigo-600={$currentPage === pageNum} class:border-gray-300={$currentPage !== pageNum}
                class:text-gray-700={$currentPage !== pageNum} class:hover:bg-gray-50={$currentPage !== pageNum}>
                {pageNum}
              </button>
            {/each}
          </div>
          <button on:click={nextPage} disabled={$currentPage === $totalPages} class="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200">Next</button>

          <select on:change={changePageSizeHandler} value={$pageSize} class="ml-2 border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500">
            <option value="10">10 per page</option>
            <option value="20">20 per page</option>
            <option value="50">50 per page</option>
          </select>
        </div>
      </div>
    {/if}
  </div>
</div>
