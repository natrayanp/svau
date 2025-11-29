<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { isAuthenticated, user } from '$lib/auth/stores';

  import {
    permissionStructure,
    loading,
    userPowerLevel,
    userMaxPower,
    systemStats,
    systemRoles,
    users,
    permissionActions
  } from '$lib/permission/stores_permission.ts';

  import { PermissionUtils } from '$lib/permission/utils_permission';

  // Import the components
  import UserDirectory from '$lib/permission/components/UserDirectory.svelte';
  import RoleDirectory from '$lib/permission/components/RoleDirectory.svelte';
  import UserRoleAssignment from '$lib/permission/components/UserRoleAssignment.svelte';
  import RoleEditPage from '$lib/permission/components/RoleEditPage.svelte';

  /* ----------------------------------------------------------
     Local UI State
  ----------------------------------------------------------- */
  let searchTerm = '';
  let expandedRole = null;
  let currentPage = 1;
  let pageSize = 10;
  let activeTab = 'roles';

  // User management state
  let selectedUserIds = [];
  let userManagementMode = 'single';
  let userManagementView = 'list';
  let isEditing = false;

  // Role management state - NEW
  let roleManagementView = 'list'; // 'list' | 'edit'
  let roleEditMode = 'view'; // 'new' | 'view' | 'edit'
  let selectedRoleId = null;

  /* ----------------------------------------------------------
     Safe derived data
  ----------------------------------------------------------- */
  $: safeUsers = $users ?? [];
  $: safeRoles = $systemRoles ?? [];
  $: safeStructure = $permissionStructure ?? { modules: [] };
  $: modules = safeStructure.modules ?? [];

  $: filteredUsers = safeUsers.filter(u =>
    (u.display_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (u.email || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  $: totalPages = Math.max(1, Math.ceil(filteredUsers.length / pageSize));
  $: paginatedUsers = filteredUsers.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  /* ----------------------------------------------------------
     Data loading
  ----------------------------------------------------------- */
  onMount(() => {
    if (!$systemStats) permissionActions.loadSystemStats();
    if (!safeRoles.length) permissionActions.loadSystemRoles();
    if (!safeStructure || !safeStructure.modules?.length) permissionActions.loadPermissionStructure();
    if (!safeUsers.length) permissionActions.loadUsers();
  });

  /* ----------------------------------------------------------
     User Management Functions
  ----------------------------------------------------------- */
  function viewUser(userId) {
    selectedUserIds = [userId];
    userManagementMode = 'single';
    userManagementView = 'user';
    isEditing = false;
    activeTab = 'users';
  }

  function editUser(userId) {
    selectedUserIds = [userId];
    userManagementMode = 'single';
    userManagementView = 'user';
    isEditing = true;
    activeTab = 'users';
  }

  function startBulkEdit(userIds) {
    selectedUserIds = userIds;
    userManagementMode = 'bulk';
    userManagementView = 'user';
    isEditing = true;
    activeTab = 'users';
  }

  function startUserMaintenance() {
    selectedUserIds = [];
    userManagementMode = 'maintenance';
    userManagementView = 'user';
    isEditing = true;
    activeTab = 'users';
  }

  function handleUserSave(updatedRoles) {
    console.log('User roles updated:', updatedRoles);
    showNotification('Roles updated successfully!', 'success');
    backToUserList();
  }

  function handleUserCancel() {
    backToUserList();
  }

  function backToUserList() {
    selectedUserIds = [];
    userManagementMode = 'single';
    userManagementView = 'list';
    isEditing = false;
  }

  /* ----------------------------------------------------------
     Role Management Functions - NEW
  ----------------------------------------------------------- */
  function viewRole(roleId) {
    selectedRoleId = roleId;
    roleEditMode = 'view';
    roleManagementView = 'edit';
    activeTab = 'roles';
  }

  function editRole(roleId) {
    selectedRoleId = roleId;
    roleEditMode = 'edit';
    roleManagementView = 'edit';
    activeTab = 'roles';
  }

  function createNewRole() {
    selectedRoleId = null;
    roleEditMode = 'new';
    roleManagementView = 'edit';
    activeTab = 'roles';
  }

  function handleRoleSave() {
    showNotification('Role saved successfully!', 'success');
    backToRoleList();
  }

  function handleRoleCancel() {
    backToRoleList();
  }

  function backToRoleList() {
    selectedRoleId = null;
    roleEditMode = 'view';
    roleManagementView = 'list';
  }

  function showNotification(message, type = 'info') {
    console.log(`${type}: ${message}`);
  }

  /* ----------------------------------------------------------
     Tab Navigation Functions
  ----------------------------------------------------------- */
  function switchToRoles() {
    activeTab = 'roles';
    userManagementView = 'list';
    roleManagementView = 'list';
  }

  function switchToUsers() {
    activeTab = 'users';
    userManagementView = 'list';
    roleManagementView = 'list';
  }

  function switchToModules() {
    activeTab = 'modules';
    userManagementView = 'list';
    roleManagementView = 'list';
  }

  /* ----------------------------------------------------------
     Other helpers
  ----------------------------------------------------------- */
  const toggleExpand = (roleKey) => {
    expandedRole = expandedRole === roleKey ? null : roleKey;
  };

  const getUsersForRole = (roleKey) =>
    safeUsers.filter(u => Array.isArray(u.roles) && u.roles.includes(roleKey));

  const goToPage = (page) => {
    if (page >= 1 && page <= totalPages) currentPage = page;
  };

  const changePageSize = (event) => {
    pageSize = parseInt(event.target.value);
    currentPage = 1;
  };

  const exportCSV = (filename, rows) => {
    const csv = rows.map(r => r.map(x => `"${x}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
  };

  const exportRoleUsersCSV = (roleKey) => {
    const roleUsers = getUsersForRole(roleKey);
    const rows = [
      ["Display Name", "Email", "User ID"],
      ...roleUsers.map(u => [u.display_name ?? '', u.email ?? '', u.id ?? ''])
    ];
    exportCSV(`${roleKey}_users.csv`, rows);
  };

  const exportAllUsersCSV = () => {
    const rows = [
      ["Display Name", "Email", "User ID"],
      ...safeUsers.map(u => [u.display_name ?? '', u.email ?? '', u.id ?? ''])
    ];
    exportCSV("all_users.csv", rows);
  };
</script>

<div class="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
  <!-- Full Width Container -->
  <div class="w-full">
    
    <!-- Header -->
    <div class="bg-white border-b border-gray-200 px-4 sm:px-6 lg:px-8 py-6">
      <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 class="text-2xl lg:text-3xl font-bold text-gray-900 bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent">
            Permission Dashboard
          </h1>
          <p class="mt-1 lg:mt-2 text-base lg:text-lg text-gray-600">
            Manage roles, users, and system permissions
          </p>
        </div>
        <div class="text-right">
          <div class="text-sm text-gray-500">Your Access Level</div>
          <div class="flex items-center space-x-2">
            <div class="w-2 h-2 lg:w-3 lg:h-3 bg-green-500 rounded-full animate-pulse"></div>
            <span class="font-semibold text-gray-900 text-sm lg:text-base">{$userPowerLevel}</span>
            <span class="text-sm text-gray-500">({$userMaxPower}/100)</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    {#if $loading.structure || $loading.roles || $loading.users}
      <div class="flex justify-center items-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        <span class="ml-4 text-gray-600">Loading dashboard data...</span>
      </div>
    {:else}

    <!-- Main Content Area -->
    <div class="px-4 sm:px-6 lg:px-8 py-6">
      <!-- Stats Overview -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6 mb-6 lg:mb-8">
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6 hover:shadow-md transition-all duration-300">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <div class="w-8 h-8 lg:w-12 lg:h-12 bg-blue-100 rounded-xl flex items-center justify-center">
                <span class="text-lg">👑</span>
              </div>
            </div>
            <div class="ml-3 lg:ml-4">
              <div class="text-xs lg:text-sm font-medium text-gray-500">Total Roles</div>
              <div class="text-xl lg:text-2xl font-bold text-gray-900">{safeRoles.length}</div>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6 hover:shadow-md transition-all duration-300">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <div class="w-8 h-8 lg:w-12 lg:h-12 bg-green-100 rounded-xl flex items-center justify-center">
                <span class="text-lg">👥</span>
              </div>
            </div>
            <div class="ml-3 lg:ml-4">
              <div class="text-xs lg:text-sm font-medium text-gray-500">Total Users</div>
              <div class="text-xl lg:text-2xl font-bold text-gray-900">{safeUsers.length}</div>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6 hover:shadow-md transition-all duration-300">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <div class="w-8 h-8 lg:w-12 lg:h-12 bg-purple-100 rounded-xl flex items-center justify-center">
                <span class="text-lg">📦</span>
              </div>
            </div>
            <div class="ml-3 lg:ml-4">
              <div class="text-xs lg:text-sm font-medium text-gray-500">Modules</div>
              <div class="text-xl lg:text-2xl font-bold text-gray-900">{modules.length}</div>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 lg:p-6 hover:shadow-md transition-all duration-300">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <div class="w-8 h-8 lg:w-12 lg:h-12 bg-orange-100 rounded-xl flex items-center justify-center">
                <span class="text-lg">🔐</span>
              </div>
            </div>
            <div class="ml-3 lg:ml-4">
              <div class="text-xs lg:text-sm font-medium text-gray-500">Permissions</div>
              <div class="text-xl lg:text-2xl font-bold text-gray-900">
                {safeStructure.metadata?.total_permissions || 0}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Main Content Tabs -->
      <div class="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden mb-6 lg:mb-8">
        <!-- Enhanced Tab Navigation with Light Blue Background -->
        <div class="bg-blue-50 border-b border-blue-200 overflow-x-auto">
          <nav class="flex min-w-max px-4 lg:px-6" aria-label="Tabs">
            <button
              class:font-semibold={activeTab === 'roles'}
              class:border-blue-500={activeTab === 'roles'}
              class:bg-blue-100={activeTab === 'roles'}
              class:border-b-2={activeTab === 'roles'}
              class:text-blue-700={activeTab === 'roles'}
              class:text-blue-600={activeTab !== 'roles'}
              class:border-transparent={activeTab !== 'roles'}
              class="py-4 lg:py-5 px-3 lg:px-4 text-base lg:text-lg font-medium whitespace-nowrap transition-all duration-200 hover:bg-blue-100 hover:text-blue-700 rounded-t-lg"
              on:click={switchToRoles}
            >
              👑 Roles Management
            </button>
            <button
              class:font-semibold={activeTab === 'users'}
              class:border-blue-500={activeTab === 'users'}
              class:bg-blue-100={activeTab === 'users'}
              class:border-b-2={activeTab === 'users'}
              class:text-blue-700={activeTab === 'users'}
              class:text-blue-600={activeTab !== 'users'}
              class:border-transparent={activeTab !== 'users'}
              class="py-4 lg:py-5 px-3 lg:px-4 text-base lg:text-lg font-medium whitespace-nowrap transition-all duration-200 hover:bg-blue-100 hover:text-blue-700 rounded-t-lg"
              on:click={switchToUsers}
            >
              👥 User Directory
            </button>
            <button
              class:font-semibold={activeTab === 'modules'}
              class:border-blue-500={activeTab === 'modules'}
              class:bg-blue-100={activeTab === 'modules'}
              class:border-b-2={activeTab === 'modules'}
              class:text-blue-700={activeTab === 'modules'}
              class:text-blue-600={activeTab !== 'modules'}
              class:border-transparent={activeTab !== 'modules'}
              class="py-4 lg:py-5 px-3 lg:px-4 text-base lg:text-lg font-medium whitespace-nowrap transition-all duration-200 hover:bg-blue-100 hover:text-blue-700 rounded-t-lg"
              on:click={switchToModules}
            >
              📦 System Modules
            </button>
          </nav>
        </div>

        <!-- Tab Content - Full Width -->
        <div class="w-full">
          <!-- Roles Tab -->
          {#if activeTab === 'roles'}
            {#if roleManagementView === 'edit'}
              <!-- Role Edit Page View -->
              <div class="w-full p-4 lg:p-6">
                <div class="mb-4">
                  <button 
                    on:click={backToRoleList}
                    class="text-indigo-600 hover:text-indigo-700 flex items-center space-x-2"
                  >
                    <span>←</span>
                    <span>Back to Role List</span>
                  </button>
                </div>
                <RoleEditPage 
                  mode={roleEditMode}
                  roleId={selectedRoleId}
                  onSave={handleRoleSave}
                  onCancel={handleRoleCancel}
                />
              </div>
            {:else}
              <!-- Role Directory List View -->
              <div class="w-full p-4 lg:p-6">
                <RoleDirectory 
                  showHeader={false}
                  compact={true}
                  enableExport={true}
                  fullWidth={true}
                  onViewRole={viewRole}
                  onEditRole={editRole}
                  onCreateRole={createNewRole}
                />
              </div>
            {/if}

          <!-- Users Tab -->
          {:else if activeTab === 'users'}
            {#if userManagementView === 'user'}
              <!-- User Role Assignment View -->
              <div class="w-full p-4 lg:p-6">
                <div class="mb-4">
                  <button 
                    on:click={backToUserList}
                    class="text-indigo-600 hover:text-indigo-700 flex items-center space-x-2"
                  >
                    <span>←</span>
                    <span>Back to User List</span>
                  </button>
                </div>
                <UserRoleAssignment 
                  userIds={selectedUserIds}
                  mode={userManagementMode}
                  showHeader={false}
                  onSave={isEditing ? handleUserSave : null}
                  onCancel={isEditing ? handleUserCancel : null}
                />
              </div>
            {:else}
              <!-- User Directory List View -->
              <div class="w-full p-4 lg:p-6">
                <UserDirectory 
                  showHeader={false}
                  compact={true}
                  enableExport={true}
                  fullWidth={true}
                  onViewUser={viewUser}
                  onEditUser={editUser}
                  onBulkEdit={startBulkEdit}
                  onUserMaintenance={startUserMaintenance}
                />
              </div>
            {/if}

          <!-- Modules Tab -->
          {:else if activeTab === 'modules'}
            <div class="p-4 lg:p-6 space-y-6">
              <div class="flex justify-between items-center">
                <h2 class="text-2xl font-bold text-gray-900">System Modules</h2>
                <div class="text-sm text-gray-500">
                  {modules.length} module{modules.length !== 1 ? 's' : ''} available
                </div>
              </div>

              {#if modules.length === 0}
                <div class="text-center py-12">
                  <div class="text-gray-400 text-6xl mb-4">📦</div>
                  <h3 class="text-lg font-medium text-gray-900 mb-2">No Modules Configured</h3>
                  <p class="text-gray-500">System modules will appear here once configured.</p>
                </div>
              {:else}
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                  {#each modules as module}
                    <div class="bg-gradient-to-br from-white to-gray-50 rounded-2xl border border-gray-200 p-6 hover:shadow-lg transition-all duration-300 group">
                      <div class="flex items-start justify-between mb-4">
                        <div class="flex items-center space-x-3">
                          <div class="w-12 h-12 rounded-xl bg-gradient-to-r from-blue-500 to-purple-600 flex items-center justify-center text-white text-lg group-hover:scale-110 transition-transform duration-200">
                            {PermissionUtils.getModuleIcon(module)}
                          </div>
                          <div>
                            <h3 class="font-bold text-gray-900 group-hover:text-gray-700 transition-colors duration-200">
                              {module.name}
                            </h3>
                            <p class="text-sm text-gray-500 mt-1">{module.menus.length} menus</p>
                          </div>
                        </div>
                      </div>
                      <p class="text-gray-600 text-sm mb-4 line-clamp-2">{module.description}</p>
                      <div class="space-y-2">
                        {#each module.menus.slice(0, 3) as menu}
                          <div class="flex items-center justify-between text-xs text-gray-500">
                            <span class="truncate">{menu.name}</span>
                            <span class="bg-gray-100 px-2 py-1 rounded">{menu.cards.length} cards</span>
                          </div>
                        {/each}
                        {#if module.menus.length > 3}
                          <div class="text-xs text-gray-400 text-center">
                            +{module.menus.length - 3} more menus
                          </div>
                        {/if}
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          {/if}
        </div>
      </div>

      <!-- Quick Actions Footer -->
      <div class="flex flex-col sm:flex-row justify-center space-y-3 sm:space-y-0 sm:space-x-4">
        {#if activeTab === 'roles' && roleManagementView === 'list'}
          <button
            on:click={createNewRole}
            class="px-4 lg:px-6 py-2 lg:py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-xl font-medium hover:from-green-700 hover:to-emerald-700 transition-all duration-200 shadow-sm hover:shadow-md flex items-center justify-center space-x-2 text-sm lg:text-base"
          >
            <span>➕</span>
            <span>Add New Role</span>
          </button>
        {/if}
        <a
          href="/permission/roles"
          class="px-4 lg:px-6 py-2 lg:py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl font-medium hover:from-indigo-700 hover:to-purple-700 transition-all duration-200 shadow-sm hover:shadow-md flex items-center justify-center space-x-2 text-sm lg:text-base"
        >
          <span>👑</span>
          <span>Roles Maintenance</span>
        </a>
        <a
          href="/permission/users"
          class="px-4 lg:px-6 py-2 lg:py-3 bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-xl font-medium hover:from-blue-700 hover:to-cyan-700 transition-all duration-200 shadow-sm hover:shadow-md flex items-center justify-center space-x-2 text-sm lg:text-base"
        >
          <span>👥</span>
          <span>User Management</span>
        </a>
      </div>
    </div>
    {/if}
  </div>
</div>

<style>
  .line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  
  .transition-all {
    transition: all 0.3s ease;
  }
</style>