<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import {
    users,
    systemRoles,
    loading,
    permissionActions
  } from '$lib/permission/stores_permission.ts';

  import { PermissionUtils } from '$lib/permission/utils_permission';

  // Export props for customization
  export let showHeader = true;
  export let compact = false;
  export let enableExport = true;
  export let fullWidth = false;
  export let onViewUser = null;
  export let onEditUser = null;
  export let onBulkEdit = null; // NEW: Bulk edit callback
  export let onUserMaintenance = null; // NEW: Maintenance callback

  /* ----------------------------------------------------------
     Local UI State - ADD BULK SELECTION
  ----------------------------------------------------------- */
  let searchTerm = '';
  let selectedRole = 'all';
  let currentPage = 1;
  let pageSize = 10;
  let selectedUserIds = []; // NEW: Track selected users for bulk actions
  let bulkActionLoading = false;

  /* ----------------------------------------------------------
     Safe derived data from stores
  ----------------------------------------------------------- */
  $: safeUsers = $users ?? [];
  $: safeRoles = $systemRoles ?? [];

  // Filter users based on search and role selection
  $: filteredUsers = safeUsers.filter(user => {
    const matchesSearch = searchTerm.trim() === '' || 
      (user.display_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (user.email || '').toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesRole = selectedRole === 'all' || 
      (user.roles || []).includes(selectedRole);
    
    return matchesSearch && matchesRole;
  });

  $: totalPages = Math.max(1, Math.ceil(filteredUsers.length / pageSize));
  $: paginatedUsers = filteredUsers.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  // Get available roles for filter dropdown
  $: availableRoles = [
    { value: 'all', label: 'All Roles' },
    ...Array.from(new Set(safeUsers.flatMap(u => u.roles || [])))
      .sort()
      .map(role => ({ 
        value: role, 
        label: role.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
      }))
  ];

  // NEW: Check if all users on current page are selected
  $: allPageUsersSelected = paginatedUsers.length > 0 && 
    paginatedUsers.every(user => selectedUserIds.includes(user.id));

  // NEW: Check if some users on current page are selected
  $: somePageUsersSelected = paginatedUsers.length > 0 && 
    paginatedUsers.some(user => selectedUserIds.includes(user.id)) &&
    !allPageUsersSelected;

  // NEW: Check if any users are selected across all pages
  $: hasSelectedUsers = selectedUserIds.length > 0;

  /* ----------------------------------------------------------
     Data loading
  ----------------------------------------------------------- */
  onMount(() => {
    // Load users and roles if not already loaded
    if (safeUsers.length === 0) {
      permissionActions.loadUsers();
    }
    if (safeRoles.length === 0) {
      permissionActions.loadSystemRoles();
    }
    
    // Check for role filter from URL
    const urlParams = new URLSearchParams($page.url.search);
    const roleFilter = urlParams.get('role');
    if (roleFilter) {
      selectedRole = roleFilter;
    }
  });

  /* ----------------------------------------------------------
     Bulk Selection Functions - NEW
  ----------------------------------------------------------- */
  function toggleUserSelection(userId) {
    if (selectedUserIds.includes(userId)) {
      selectedUserIds = selectedUserIds.filter(id => id !== userId);
    } else {
      selectedUserIds = [...selectedUserIds, userId];
    }
  }

  function toggleAllPageUsers() {
    if (allPageUsersSelected) {
      // Deselect all users on current page
      selectedUserIds = selectedUserIds.filter(id => 
        !paginatedUsers.some(user => user.id === id)
      );
    } else {
      // Select all users on current page
      const pageUserIds = paginatedUsers.map(user => user.id);
      selectedUserIds = [...new Set([...selectedUserIds, ...pageUserIds])];
    }
  }

  function selectAllFilteredUsers() {
    if (selectedUserIds.length === filteredUsers.length) {
      // Deselect all filtered users
      selectedUserIds = [];
    } else {
      // Select all filtered users
      selectedUserIds = filteredUsers.map(user => user.id);
    }
  }

  function startBulkEdit() {
    if (selectedUserIds.length >= 2 && onBulkEdit) {
      onBulkEdit(selectedUserIds);
    }
  }

  function startUserMaintenance() {
    if (onUserMaintenance) {
      onUserMaintenance();
    }
  }

  function clearSelection() {
    selectedUserIds = [];
  }

  /* ----------------------------------------------------------
     Helpers
  ----------------------------------------------------------- */
  const goToPage = (page) => {
    if (page >= 1 && page <= totalPages) currentPage = page;
  };

  const changePageSize = (event) => {
    pageSize = parseInt(event.target.value);
    currentPage = 1;
  };

  // Calculate user statistics from store data
  $: userStats = {
    total: safeUsers.length,
    admins: safeUsers.filter(u => (u.roles || []).includes('admin')).length,
    highPower: safeUsers.filter(u => (u.roles || []).includes('admin') || (u.roles || []).includes('user_manager')).length,
    multiRole: safeUsers.filter(u => (u.roles || []).length > 1).length
  };

  /* ----------------------------------------------------------
     User Actions
  ----------------------------------------------------------- */
  const viewUser = (userId) => {
    if (onViewUser) {
      onViewUser(userId);
    }
  };

  const editUser = (userId) => {
    if (onEditUser) {
      onEditUser(userId);
    }
  };

  const deleteUser = (userId, userName) => {
    if (confirm(`Are you sure you want to delete user "${userName}"?`)) {
      console.log(`Deleting user ${userId}`);
      // permissionActions.deleteUser(userId);
    }
  };

  /* ----------------------------------------------------------
     CSV Export (using store data)
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

  const exportAllUsersCSV = () => {
    const rows = [
      ["Display Name", "Email", "User ID", "Roles", "Organization", "Status", "Joined Date"],
      ...safeUsers.map(u => [
        u.display_name ?? '', 
        u.email ?? '', 
        u.id ?? '',
        (u.roles || []).join(', '),
        `Org ${u.organization_id}`,
        u.email_verified ? 'Verified' : 'Pending',
        new Date(u.created_at).toLocaleDateString()
      ])
    ];
    exportCSV("all_users.csv", rows);
  };

  const exportSelectedUsersCSV = () => {
    const selectedUsers = safeUsers.filter(u => selectedUserIds.includes(u.id));
    const rows = [
      ["Display Name", "Email", "User ID", "Roles", "Organization", "Status", "Joined Date"],
      ...selectedUsers.map(u => [
        u.display_name ?? '', 
        u.email ?? '', 
        u.id ?? '',
        (u.roles || []).join(', '),
        `Org ${u.organization_id}`,
        u.email_verified ? 'Verified' : 'Pending',
        new Date(u.created_at).toLocaleDateString()
      ])
    ];
    exportCSV("selected_users.csv", rows);
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
            <h1 class="text-3xl font-bold text-gray-900">User Management</h1>
            <p class="mt-2 text-lg text-gray-600">
              Assign roles and manage user permissions
            </p>
          </div>
          <div class="flex items-center space-x-4">
            <!-- Bulk Actions -->
            {#if hasSelectedUsers}
              <div class="flex items-center space-x-3 bg-blue-50 rounded-lg px-4 py-2 border border-blue-200">
                <span class="text-sm text-blue-700 font-medium">
                  {selectedUserIds.length} user{selectedUserIds.length !== 1 ? 's' : ''} selected
                </span>
                <button
                  on:click={startBulkEdit}
                  disabled={selectedUserIds.length < 2}
                  class="bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-indigo-400 px-3 py-1 rounded text-sm font-medium transition-colors duration-200 flex items-center space-x-2"
                  title={selectedUserIds.length < 2 ? 'Select at least 2 users for bulk edit' : 'Edit selected users'}
                >
                  <span>👥</span>
                  <span>Bulk Edit</span>
                </button>
                <button
                  on:click={exportSelectedUsersCSV}
                  class="bg-green-600 text-white hover:bg-green-700 px-3 py-1 rounded text-sm font-medium transition-colors duration-200 flex items-center space-x-2"
                  title="Export selected users to CSV"
                >
                  <span>📥</span>
                  <span>Export</span>
                </button>
                <button
                  on:click={clearSelection}
                  class="text-blue-600 hover:text-blue-700 text-sm font-medium"
                >
                  Clear
                </button>
              </div>
            {/if}
            
            <!-- User Maintenance Button -->
            <button
              on:click={startUserMaintenance}
              class="bg-blue-600 text-white hover:bg-blue-700 px-4 py-2 rounded-lg font-medium transition-colors duration-200 flex items-center space-x-2"
              title="Add new users and manage roles"
            >
              <span>⚙️</span>
              <span>User Maintenance</span>
            </button>
          </div>
        </div>
      </div>
    {/if}

    <!-- Loading State -->
    {#if $loading.users}
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
            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <span class="text-gray-400">🔍</span>
            </div>
            <input
              type="text"
              bind:value={searchTerm}
              placeholder="Search users..."
              class="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 w-64"
            />
          </div>

          <!-- Role Filter -->
          <select
            bind:value={selectedRole}
            class="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            {#each availableRoles as role}
              <option value={role.value}>{role.label}</option>
            {/each}
          </select>

          <!-- Export Button -->
          {#if enableExport}
            <button
              on:click={exportAllUsersCSV}
              class="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors duration-200 flex items-center space-x-2"
            >
              <span>📥</span>
              <span>Export CSV</span>
            </button>
          {/if}

          <!-- Select All Filtered Button -->
          {#if filteredUsers.length > 0}
            <button
              on:click={selectAllFilteredUsers}
              class="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 transition-colors duration-200 flex items-center space-x-2"
            >
              <span>{selectedUserIds.length === filteredUsers.length ? '☑' : '☐'}</span>
              <span>
                {selectedUserIds.length === filteredUsers.length ? 
                 'Deselect All' : 
                 `Select All ${filteredUsers.length} Users`}
              </span>
            </button>
          {/if}


          {#if hasSelectedUsers}
              <div class="flex items-center space-x-3 bg-blue-50 rounded-lg px-4 py-2 border border-blue-200">
                <span class="text-sm text-blue-700 font-medium">
                  {selectedUserIds.length} user{selectedUserIds.length !== 1 ? 's' : ''} selected
                </span>
                <button
                  on:click={startBulkEdit}
                  disabled={selectedUserIds.length < 2}
                  class="bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-indigo-400 px-3 py-1 rounded text-sm font-medium transition-colors duration-200 flex items-center space-x-2"
                  title={selectedUserIds.length < 2 ? 'Select at least 2 users for bulk edit' : 'Edit selected users'}
                >
                  <span>👥</span>
                  <span>Bulk Edit</span>
                </button>
                <!--button
                  on:click={exportSelectedUsersCSV}
                  class="bg-green-600 text-white hover:bg-green-700 px-3 py-1 rounded text-sm font-medium transition-colors duration-200 flex items-center space-x-2"
                  title="Export selected users to CSV"
                >
                  <span>📥</span>
                  <span>Export</span>
                </button-->
                <button
                  on:click={clearSelection}
                  class="text-blue-600 hover:text-blue-700 text-sm font-medium"
                >
                  Clear
                </button>
              </div>
            {/if}

        </div>

        <div class="text-sm text-gray-500">
          {filteredUsers.length} {filteredUsers.length === 1 ? 'user' : 'users'} found
          {#if hasSelectedUsers}
            · {selectedUserIds.length} selected
          {/if}
        </div>
      </div>
    </div>

    <!-- Users Table - Full Width -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden w-full">
      <div class="overflow-x-auto w-full">
        <table class="min-w-full divide-y divide-gray-200 w-full">
          <thead class="bg-gray-50">
            <tr>
              <!-- NEW: Checkbox column for bulk selection -->
              <th class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-12">
                <input
                  type="checkbox"
                  checked={allPageUsersSelected}
                  indeterminate={somePageUsersSelected}
                  on:change={toggleAllPageUsers}
                  class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                />
              </th>
              <th class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/4">User</th>
              <th class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/4">Roles</th>
              <th class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/6">Organization</th>
              <th class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/6">Status</th>
              <th class="px-4 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/6">Joined</th>
              <th class="px-4 sm:px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider w-1/6">Actions</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            {#each paginatedUsers as user}
              <tr class="hover:bg-gray-50 transition-colors duration-150 {selectedUserIds.includes(user.id) ? 'bg-blue-50' : ''}">
                <!-- NEW: Checkbox for each user -->
                <td class="px-4 sm:px-6 py-4 whitespace-nowrap">
                  <input
                    type="checkbox"
                    checked={selectedUserIds.includes(user.id)}
                    on:change={() => toggleUserSelection(user.id)}
                    class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                  />
                </td>

                <!-- User Info -->
                <td class="px-4 sm:px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center">
                    <div class="flex-shrink-0 h-10 w-10 bg-indigo-100 rounded-full flex items-center justify-center">
                      <span class="text-indigo-600 font-semibold text-sm">
                        {(user.display_name || 'UU').substring(0, 2).toUpperCase()}
                      </span>
                    </div>
                    <div class="ml-4">
                      <div class="text-sm font-medium text-gray-900">{user.display_name || 'Unknown User'}</div>
                      <div class="text-sm text-gray-500">{user.email}</div>
                    </div>
                  </div>
                </td>

                <!-- Roles -->
                <td class="px-4 sm:px-6 py-4 whitespace-nowrap">
                  <div class="flex flex-wrap gap-1">
                    {#each (user.roles || []) as role}
                      <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium {
                        role === 'admin' ? 'bg-red-100 text-red-800' :
                        role === 'user_manager' ? 'bg-orange-100 text-orange-800' :
                        role === 'content_editor' ? 'bg-yellow-100 text-yellow-800' :
                        role === 'creator' ? 'bg-purple-100 text-purple-800' :
                        role === 'moderator' ? 'bg-blue-100 text-blue-800' :
                        'bg-gray-100 text-gray-800'
                      }">
                        {role.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
                      </span>
                    {/each}
                    {#if (user.roles || []).length === 0}
                      <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                        No roles
                      </span>
                    {/if}
                  </div>
                </td>

                <!-- Organization -->
                <td class="px-4 sm:px-6 py-4 whitespace-nowrap">
                  <div class="text-sm text-gray-900">Org #{user.organization_id}</div>
                </td>

                <!-- Status -->
                <td class="px-4 sm:px-6 py-4 whitespace-nowrap">
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

                <!-- Joined Date -->
                <td class="px-4 sm:px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {new Date(user.created_at).toLocaleDateString()}
                </td>

                <!-- Actions -->
                <td class="px-4 sm:px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <div class="flex justify-end space-x-2">
                    <button
                      on:click={() => viewUser(user.id)}
                      class="p-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors duration-200"
                      title="View User Roles"
                    >
                      👁️
                    </button>
                    <button
                      on:click={() => editUser(user.id)}
                      class="p-2 bg-green-50 text-green-600 rounded-lg hover:bg-green-100 transition-colors duration-200"
                      title="Edit User Roles"
                    >
                      ✏️
                    </button>
                    <button
                      on:click={() => deleteUser(user.id, user.display_name)}
                      class="p-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors duration-200"
                      title="Delete User"
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
      {#if filteredUsers.length === 0}
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
    {#if filteredUsers.length > 0}
      <div class="flex flex-col sm:flex-row items-center justify-between gap-4 pt-6 w-full">
        <div class="text-sm text-gray-500 text-center sm:text-left">
          Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, filteredUsers.length)} of {filteredUsers.length} users
          {#if hasSelectedUsers}
            · {selectedUserIds.length} selected
          {/if}
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

    {/if}
  </div>
</div>

<style>
  /* Style for indeterminate checkbox state */
  input[type="checkbox"]:indeterminate {
    background-color: #6366f1;
    border-color: #6366f1;
  }
</style>