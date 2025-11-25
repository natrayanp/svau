<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';

  let searchTerm = '';
  let selectedRole = 'all';
  let users = [];
  let filteredUsers = [];

  // Mock users data
  const mockUsers = [
    {
      id: 1,
      name: 'John Doe',
      email: 'john@example.com',
      roles: ['creator', 'user_manager'],
      effective_permissions: 18,
      power_level: 80,
      last_active: '2024-01-15'
    },
    {
      id: 2,
      name: 'Jane Smith',
      email: 'jane@example.com',
      roles: ['basic'],
      effective_permissions: 8,
      power_level: 10,
      last_active: '2024-01-14'
    },
    {
      id: 3,
      name: 'Admin User',
      email: 'admin@example.com',
      roles: ['admin'],
      effective_permissions: 35,
      power_level: 100,
      last_active: '2024-01-15'
    },
    {
      id: 4,
      name: 'Content Creator',
      email: 'creator@example.com',
      roles: ['creator'],
      effective_permissions: 15,
      power_level: 30,
      last_active: '2024-01-13'
    }
  ];

  const roles = [
    { value: 'all', label: 'All Roles' },
    { value: 'basic', label: 'Basic' },
    { value: 'creator', label: 'Creator' },
    { value: 'moderator', label: 'Moderator' },
    { value: 'admin', label: 'Admin' }
  ];

  onMount(() => {
    users = mockUsers;
    filteredUsers = mockUsers;
    
    // Check for role filter from URL
    const urlParams = new URLSearchParams($page.url.search);
    const roleFilter = urlParams.get('role');
    if (roleFilter) {
      selectedRole = roleFilter;
      filterUsers();
    }
  });

  function filterUsers() {
    let filtered = users;

    // Filter by search term
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(user =>
        user.name.toLowerCase().includes(term) ||
        user.email.toLowerCase().includes(term)
      );
    }

    // Filter by role
    if (selectedRole !== 'all') {
      filtered = filtered.filter(user =>
        user.roles.includes(selectedRole)
      );
    }

    filteredUsers = filtered;
  }

  $: {
    filterUsers();
  }

  function getPowerLevelIcon(power) {
    if (power <= 30) return '🟢';
    if (power <= 60) return '🟡';
    if (power <= 80) return '🟠';
    return '🔴';
  }

  function getPowerLevelLabel(power) {
    if (power <= 30) return 'Low';
    if (power <= 60) return 'Medium';
    if (power <= 80) return 'High';
    return 'Critical';
  }
</script>

<svelte:head>
  <title>User Management - AuthApp</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 py-8">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <!-- Header -->
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
          <button class="bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-lg font-medium transition-colors duration-200">
            📋 Bulk Actions
          </button>
        </div>
      </div>
    </div>

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
            {#each roles as role}
              <option value={role.value}>{role.label}</option>
            {/each}
          </select>
        </div>

        <div class="text-sm text-gray-500">
          {filteredUsers.length} {filteredUsers.length === 1 ? 'user' : 'users'} found
        </div>
      </div>
    </div>

    <!-- Users Table -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                User
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Roles
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Permissions
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Power Level
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Last Active
              </th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            {#each filteredUsers as user}
              <tr class="hover:bg-gray-50 transition-colors duration-150">
                <!-- User Info -->
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center">
                    <div class="flex-shrink-0 h-10 w-10 bg-indigo-100 rounded-full flex items-center justify-center">
                      <span class="text-indigo-600 font-semibold text-sm">
                        {user.name.split(' ').map(n => n[0]).join('')}
                      </span>
                    </div>
                    <div class="ml-4">
                      <div class="text-sm font-medium text-gray-900">{user.name}</div>
                      <div class="text-sm text-gray-500">{user.email}</div>
                    </div>
                  </div>
                </td>

                <!-- Roles -->
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex flex-wrap gap-1">
                    {#each user.roles as role}
                      <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium {
                        role === 'admin' ? 'bg-red-100 text-red-800' :
                        role === 'moderator' ? 'bg-orange-100 text-orange-800' :
                        role === 'creator' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-blue-100 text-blue-800'
                      }}">
                        {role}
                      </span>
                    {/each}
                  </div>
                </td>

                <!-- Permissions -->
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="text-sm text-gray-900">{user.effective_permissions} permissions</div>
                </td>

                <!-- Power Level -->
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center space-x-2">
                    <span class="text-lg">{getPowerLevelIcon(user.power_level)}</span>
                    <div>
                      <div class="text-sm font-medium text-gray-900">{getPowerLevelLabel(user.power_level)}</div>
                      <div class="text-xs text-gray-500">{user.power_level}/100</div>
                    </div>
                  </div>
                </td>

                <!-- Last Active -->
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {user.last_active}
                </td>

                <!-- Actions -->
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <a
                    href="/permission/users/{user.id}"
                    class="text-indigo-600 hover:text-indigo-900 mr-4"
                  >
                    Manage Roles
                  </a>
                  <button class="text-gray-400 hover:text-gray-600">
                    ⋮
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Empty State -->
      {#if filteredUsers.length === 0}
        <div class="text-center py-12">
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

    <!-- Stats Summary -->
    <div class="mt-6 grid grid-cols-1 md:grid-cols-4 gap-6">
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 text-center">
        <div class="text-2xl font-bold text-gray-900">{users.length}</div>
        <div class="text-sm text-gray-500">Total Users</div>
      </div>
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 text-center">
        <div class="text-2xl font-bold text-gray-900">{users.filter(u => u.roles.includes('admin')).length}</div>
        <div class="text-sm text-gray-500">Admins</div>
      </div>
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 text-center">
        <div class="text-2xl font-bold text-gray-900">{users.filter(u => u.power_level >= 80).length}</div>
        <div class="text-sm text-gray-500">High Power</div>
      </div>
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 text-center">
        <div class="text-2xl font-bold text-gray-900">{users.filter(u => u.roles.length > 1).length}</div>
        <div class="text-sm text-gray-500">Multi-Role</div>
      </div>
    </div>
  </div>
</div>