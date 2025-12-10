<script lang="ts">
  import { onMount } from 'svelte';
  import { page as pageStore } from '$app/stores';
  import { usersStore, rolesStore } from '$lib/permission/stores/permission_entity_stores';
  import { usePageSelection, usePaginationControls, buildFilter, useMutations, useLookup } from '$lib/common/controls';
  import type { User } from '$lib/permission/types_permission';

  // Extract inner Svelte writables exposed by the factory
  const { pagination: usersPagination, loading: usersLoading } = usersStore;
  const { pagination: rolesPagination } = rolesStore;

    const { deleteItem:userDelete } = useMutations(usersStore);
    const { getEntities:getUserbyid } = useLookup(usersStore);

  // Props
  export let showHeader: boolean = true;
  export let enableExport: boolean = true;
  export let fullWidth: boolean = false;
  export let onViewUser: ((userId: string) => void) | null = null;
  export let onEditUser: ((userId: string) => void) | null = null;
  export let onBulkEdit: ((userIds: string[]) => void) | null = null;
  export let onUserMaintenance: (() => void) | null = null;

  // Local UI state
  let searchTerm = '';
  let selectedRole: string = 'all';

  // Selection helpers (derived stores)
const {
  selectedIds: selectedUserIds,
  toggleSelection,
  clearSelection,
  toggleAllPageItems,
  allPageItemsSelected,
  somePageItemsSelected,
  hasSelectedItems
} = usePageSelection(usersPagination, 'user_id');


  // Pagination helpers (derived stores)
const {
  currentPage,
  pageSize,
  totalPages,
  totalItems,
  goToPage,
  nextPage,
  prevPage,
  setPageSize
} = usePaginationControls(usersStore);



  // Debounce
  let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;
  const SEARCH_DEBOUNCE_MS = 300;
  let rolesList: any[] = [];
  let availableRoles: { value: string; label: string }[] = [];

  // Reactive subscriptions
  $: pagedUsers = $usersPagination?.items ?? [];
  $: loadingUsers = $usersLoading ?? false;

  $:rolesList = Array.isArray($rolesPagination) ? $rolesPagination : $rolesPagination?.items ?? [];
  $: availableRoles = [
    { value: 'all', label: 'All Roles' },
    ...(
      rolesList.length > 0
        ? rolesList.map((r: any) => r.role_id ?? r.name ?? r).filter(Boolean)
        : Array.from(new Set((pagedUsers ?? []).flatMap((u: any) => u.roles ?? [])))
    )
      .sort()
      .map((role: string) => ({
        value: role,
        label: role.split('_').map(w => w[0]?.toUpperCase() + w.slice(1)).join(' ')
      }))
  ];

  // Build filter using generic builder
  function applyFilter() {
    console.log('🔍 applyFilter called with:', {
      searchTerm,
      selectedRole,
      currentPage: $currentPage,
      pageSize: $pageSize
    });
    
    const filter: any = {};
    
    // Add search term
    if (searchTerm.trim()) {
      filter.q = searchTerm.trim();
    }
    
    // Add role filter (if not "all")
    if (selectedRole && selectedRole !== 'all') {
      filter.roles = selectedRole;  // Make sure this is the correct field name
      console.log('✅ Role filter added:', filter.roles);
    }
    
    console.log('📤 Filter being sent to store:', filter);
    
    usersStore.setView($currentPage, $pageSize, { queryFilter: filter });
  }

  // Single place to request data
  function loadUsers(page: number = $currentPage) {
    
    goToPage(page);
    applyFilter();
  }

  // Handlers
  function debouncedSearchInput() {
    if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
      goToPage(1);
      loadUsers(1);
    }, SEARCH_DEBOUNCE_MS);
  }

  function handleRoleChange(e: Event) {
    const newRole = (e.target as HTMLSelectElement).value;
    console.log('🔄 Role changed from', selectedRole, 'to', newRole);
    selectedRole = newRole;
    goToPage(1);
    loadUsers(1);
  }

  function changePageSize(event: Event) {
    const newSize = parseInt((event.target as HTMLSelectElement).value) || 10;
    setPageSize(newSize);
    goToPage(1);
    loadUsers(1);
  }

  // Bulk actions
  function startBulkEdit() {
    if ($selectedUserIds.length >= 2 && onBulkEdit) onBulkEdit($selectedUserIds);
  }

  function startUserMaintenance() {
    onUserMaintenance?.();
  }

  // Select or deselect all users on the current page
  function toggleAllPageUsers() {
    console.log(pagedUsers);
    toggleAllPageItems(pagedUsers);
  }


  // Stats
  $: userStats = {
    total: $totalItems,
    admins: $usersPagination?.meta?.adminsCount ?? pagedUsers.filter((u: any) => (u.roles ?? []).includes('admin')).length,
    highPower: $usersPagination?.meta?.highPowerCount ?? pagedUsers.filter((u: any) => (u.roles ?? []).includes('admin') || (u.roles ?? []).includes('user_manager')).length,
    multiRole: $usersPagination?.meta?.multiRoleCount ?? pagedUsers.filter((u: any) => (u.roles ?? []).length > 1).length
  };

  const viewUser = (id: string) => onViewUser?.(id);
  const editUser = (id: string) => onEditUser?.(id);
  const deleteUser = async(
      users: (string | number)| (string | number) [], // Accepts individual or array
  ) => {
      const userArray = Array.isArray(users) ? users : [users];
      if (userArray.length === 0) {
          return;
      }
      let primaryname = userArray.length === 1?getUserbyid(userArray[0]):'';

      const confirmationText = userArray.length === 1
          ? `Delete user "${primaryname}"?`
          : `Delete ${userArray.length} users?`;
    
      if (confirm(confirmationText)) {
          userDelete?.(userArray); 
          loadUsers($currentPage); 
      }
  };

  // CSV export helpers remain unchanged
  const exportCSV = (filename: string, rows: (string|number)[][]) => { /* ... */ };
  const exportAllUsersCSV = () => { /* ... */ };
  const exportSelectedUsersCSV = () => { /* ... */ };

  // Clear selection when pagination changes
  $: {
    if (pagedUsers.length > 0) {
      const currentPageIds = new Set(pagedUsers.map((u: any) => String(u.user_id)));
      selectedUserIds.set($selectedUserIds.filter(id => currentPageIds.has(id)));
    } else {
      clearSelection();
    }
  }

  // On mount: load roles and first page
  $: pageUrl = $pageStore?.url;
  onMount(() => {
    console.log('loadusers');
    if ((rolesList ?? []).length === 0) rolesStore.setView(1, 100);
    try {
      const urlParams = new URLSearchParams(pageUrl?.search ?? '');
      const roleFilter = urlParams.get('role');
      if (roleFilter) selectedRole = roleFilter;
    } catch (e) { /* ignore */ }
    loadUsers(1);
  });
</script>

<!-- Full Width Container -->
<div class="{fullWidth ? 'w-full' : 'min-h-screen bg-gray-50'} {!fullWidth ? 'py-8' : ''}">
  <div class="{fullWidth ? 'w-full' : 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-8'}">

    <!-- Header -->
    {#if showHeader}
      <div class="mb-8">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-3xl font-bold text-gray-900">User Management</h1>
            <p class="mt-2 text-lg text-gray-600">Assign roles and manage user permissions</p>
          </div>
          <div class="flex items-center space-x-4">
            {#if $hasSelectedItems}
              <div class="flex items-center space-x-3 bg-blue-50 rounded-lg px-4 py-2 border border-blue-200">
                <span class="text-sm text-blue-700 font-medium">
                  {$selectedUserIds.length} user{$selectedUserIds.length !== 1 ? 's' : ''} selected
                </span>
                <button on:click={startBulkEdit} disabled={$selectedUserIds.length < 2}
                  class="bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-indigo-400 px-3 py-1 rounded text-sm font-medium flex items-center space-x-2">
                  <span>👥</span><span>Bulk Edit</span>
                </button>
                <button on:click={exportSelectedUsersCSV}
                  class="bg-green-600 text-white hover:bg-green-700 px-3 py-1 rounded text-sm font-medium flex items-center space-x-2">
                  <span>📥</span><span>Export</span>
                </button>
                <button on:click={clearSelection} class="text-blue-600 hover:text-blue-700 text-sm font-medium">Clear</button>
              </div>
            {/if}

            <button on:click={startUserMaintenance}
              class="bg-blue-600 text-white hover:bg-blue-700 px-4 py-2 rounded-lg font-medium flex items-center space-x-2"
              title="Add new users and manage roles">
              <span>⚙️</span><span>User Maintenance</span>
            </button>
          </div>
        </div>
      </div>
    {/if}
    <!-- Loading State -->
    {#if loadingUsers}
      <div class="flex justify-center items-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        <span class="ml-4 text-gray-600">Loading users...</span>
      </div>
    {:else}
    <!-- Filters -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div class="flex flex-col sm:flex-row sm:items-center space-y-4 sm:space-y-0 sm:space-x-4">
          <!-- Search -->
          <div class="relative">
            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><span class="text-gray-400">🔍</span></div>
            <input type="text" bind:value={searchTerm} on:input={debouncedSearchInput}
              placeholder="Search users..."
              class="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 w-64" />
          </div>

          <!-- Role Filter -->
          <select bind:value={selectedRole} on:change={handleRoleChange}
            class="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500">
            {#each availableRoles as role}
              <option value={role.value}>{role.label}</option>
            {/each}
          </select>

          <!-- Export -->
          {#if enableExport}
            <button on:click={exportAllUsersCSV}
              class="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 flex items-center space-x-2">
              <span>📥</span><span>Export CSV</span>
            </button>
          {/if}

          <!-- Page Selection -->
          {#if pagedUsers.length > 0}
            <button on:click={toggleAllPageUsers}
              class="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 flex items-center space-x-2">
              <span>{$allPageItemsSelected ? '☑' : $somePageItemsSelected ? '◩' : '☐'}</span>
              <span>{$allPageItemsSelected ? 'Deselect Page' : `Select Page (${pagedUsers.length})`}</span>
            </button>
            {#if $somePageItemsSelected | $allPageItemsSelected }
            <button on:click={() => deleteUser($selectedUserIds)}
              class="px-4 py-2 bg-red-100 text-red-700 rounded-lg text-sm font-medium hover:bg-red-200 flex items-center space-x-2">
              <span>{`Delete ${($selectedUserIds).length} Users`}</span>
            </button>
            {/if}
          {/if}
        </div>

        <div class="text-sm text-gray-500">
          {$totalItems} {$totalItems === 1 ? 'user' : 'users'} found
          {#if $hasSelectedItems} · {$selectedUserIds.length} selected {/if}
        </div>
      </div>
    </div>
    <!-- Users Table -->
<div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden w-full">
  <div class="overflow-x-auto w-full">
    <table class="min-w-full divide-y divide-gray-200 w-full">
      <thead class="bg-gray-50">
        <tr>
          <th class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-12">
            <input type="checkbox"
              checked={$allPageItemsSelected}
              indeterminate={$somePageItemsSelected}
              on:change={toggleAllPageUsers}
              class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded" />
          </th>
          <th class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/4">User</th>
          <th class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/4">Roles</th>
          <th class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/6">Organization</th>
          <th class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/6">Status</th>
          <th class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/6">Joined</th>
          <th class="px-4 sm:px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider w-1/6">Actions</th>
        </tr>
      </thead>

      <!-- ✅ open tbody once -->
      <tbody class="bg-white divide-y divide-gray-200">
        {#each pagedUsers as user}
          <tr class="hover:bg-gray-50 transition-colors"
              class:bg-blue-50={$selectedUserIds.includes(String(user.user_id))}>

            <!-- Selection Checkbox -->
            <td class="px-4 py-4">
              <input type="checkbox"
                checked={$selectedUserIds.includes(String(user.user_id))}
                on:change={() => toggleSelection(user.user_id)}
                class="h-4 w-4 text-indigo-600 border-gray-300 rounded" />
            </td>

            <!-- User Info -->
            <td class="px-4 py-4">
              <div class="flex items-center">
                <div class="h-10 w-10 bg-indigo-100 rounded-full flex items-center justify-center">
                  <span class="text-indigo-600 font-semibold text-sm">
                    {(user.display_name || 'UU').substring(0,2).toUpperCase()}
                  </span>
                </div>
                <div class="ml-4">
                  <div class="text-sm font-medium text-gray-900">{user.display_name || 'Unknown User'}</div>
                  <div class="text-sm text-gray-500">{user.email}</div>
                </div>
              </div>
            </td>

            <!-- Roles -->
            <td class="px-4 py-4">
              <div class="flex flex-wrap gap-1">
                {#each (user.roles || []) as role}
                  <span class="inline-flex px-2 py-1 rounded-full text-xs font-medium
                    { role === 'admin' ? 'bg-red-100 text-red-800'
                    : role === 'user_manager' ? 'bg-orange-100 text-orange-800'
                    : 'bg-gray-100 text-gray-800' }">
                    {role.split('_').map(w => w[0]?.toUpperCase() + w.slice(1)).join(' ')}
                  </span>
                {/each}
                {#if (user.roles || []).length === 0}
                  <span class="inline-flex px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                    No roles
                  </span>
                {/if}
              </div>
            </td>

            <!-- Organization -->
            <td class="px-4 py-4">
              <div class="text-sm text-gray-900">Org #{user.org_id ?? user.org_id}</div>
            </td>

            <!-- Status -->
            <td class="px-4 py-4">
              <div class="flex items-center">
                {#if user.email_verified}
                  <div class="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                  <span class="text-sm text-gray-900">Verified</span>
                {:else}
                  <div class="w-2 h-2 bg-yellow-500 rounded-full mr-2"></div>
                  <span class="text-sm text-gray-900">Pending</span>
                {/if}
              </div>
            </td>

            <!-- Joined -->
            <td class="px-4 py-4 text-sm text-gray-500">
              {user.created_at ? new Date(user.created_at).toLocaleDateString() : ''}
            </td>

            <!-- Actions -->
            <td class="px-4 py-4 text-right text-sm font-medium">
              <div class="flex justify-end space-x-2">
                <button on:click={() => viewUser(user.user_id)} class="p-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100">👁️</button>
                <button on:click={() => editUser(user.user_id)} class="p-2 bg-green-50 text-green-600 rounded-lg hover:bg-green-100">✏️</button>
                <button on:click={() => deleteUser(user.user_id)} class="p-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100">🗑️</button>
              </div>
            </td>
          </tr>
        {/each}
      </tbody> <!-- ✅ close tbody once -->
    </table>
  </div>

  {#if pagedUsers.length === 0}
    <div class="text-center py-12 w-full">
      <div class="text-gray-400 text-6xl mb-4">👥</div>
      <h3 class="text-lg font-medium text-gray-900 mb-2">No users found</h3>
      <p class="text-gray-500">
        {#if searchTerm || selectedRole !== 'all'}
          Try adjusting your search or filter criteria
        {:else}
          No users available in the system
        {/if}
      </p>
    </div>
  {/if}
</div>


    <!-- Pagination -->
{#if $totalItems > 0}
  <div class="flex flex-col sm:flex-row items-center justify-between gap-4 pt-6 w-full">
    <div class="text-sm text-gray-500 text-center sm:text-left">
      Showing {((($currentPage - 1) * $pageSize) + 1)}
      to {Math.min($currentPage * $pageSize, $totalItems)} of {$totalItems} users
      {#if $hasSelectedItems} · {$selectedUserIds.length} selected {/if}
    </div>

    <div class="flex items-center space-x-2">
      <!-- Previous -->
      <button on:click={prevPage} disabled={$currentPage === 1}
        class="px-4 py-2 border border-gray-300 rounded-lg text-sm">
        Previous
      </button>

      <!-- Page Numbers -->
      <div class="flex items-center space-x-1">
        {#each Array.from({ length: Math.min(5, $totalPages) }, (_, i) => {
          let pageNum;
          if ($totalPages <= 5) pageNum = i + 1;
          else if ($currentPage <= 3) pageNum = i + 1;
          else if ($currentPage >= $totalPages - 2) pageNum = $totalPages - 4 + i;
          else pageNum = $currentPage - 2 + i;
          return pageNum;
        }) as pageNum}
          <button on:click={() => goToPage(pageNum)}
            class:bg-indigo-600={$currentPage === pageNum}
            class:text-white={$currentPage === pageNum}
            class="w-10 h-10 rounded-lg text-sm font-medium border transition-colors duration-200"
            class:border-indigo-600={$currentPage === pageNum}
            class:border-gray-300={$currentPage !== pageNum}
            class:text-gray-700={$currentPage !== pageNum}>
            {pageNum}
          </button>
        {/each}
      </div>

      <!-- Next -->
      <button on:click={nextPage}
              disabled={$currentPage === $totalPages || loadingUsers}
              class="px-4 py-2 border border-gray-300 rounded-lg text-sm">
        Next
      </button>

      <!-- Page Size -->
      <select class="ml-2 px-2 py-2 text-sm border border-gray-300 rounded-lg bg-white"
              on:change={changePageSize} value={$pageSize}>
        <option value="10">10</option>
        <option value="20">20</option>
        <option value="50">50</option>
      </select>
    </div>
  </div>
{/if}

    <!-- Stats Summary -->
    <div class="mt-6 grid grid-cols-1 md:grid-cols-4 gap-6 w-full">
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 text-center">
        <div class="text-2xl font-bold text-gray-900">{userStats.total}</div>
        <div class="text-sm text-gray-500">Total Users</div>
      </div>
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 text-center">
        <div class="text-2xl font-bold text-gray-900">{userStats.admins}</div>
        <div class="text-sm text-gray-500">Admins</div>
      </div>
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 text-center">
        <div class="text-2xl font-bold text-gray-900">{userStats.highPower}</div>
        <div class="text-sm text-gray-500">High Power</div>
      </div>
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 text-center">
        <div class="text-2xl font-bold text-gray-900">{userStats.multiRole}</div>
        <div class="text-sm text-gray-500">Multi-Role</div>
      </div>
    </div>
    {/if} <!-- closes {:else} after loading state -->
  </div>
</div>

<style>
  /* Indeterminate checkbox visual */
  input[type="checkbox"]:indeterminate {
    background-color: #6366f1; /* Indigo-500 */
    border-color: #6366f1;
  }

  /* Spinner animation */
  .animate-spin {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to   { transform: rotate(360deg); }
  }
</style>
