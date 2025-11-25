<script>
  import { page } from '$app/stores';
  import { isAuthenticated, user } from '$lib/auth/stores';
  import { 
    permissionStructure, 
    loading, 
    userPowerLevel, 
    userMaxPower 
  } from '$lib/permission/stores_permission';
  import { PermissionUtils } from '$lib/permission/utils_permission';

  let currentTab = 'overview';
  
  // Mock data for demonstration
  const userStats = {
    total_roles: 4,
    total_users: 156,
    total_permissions: 35,
    recent_activity: 12
  };

  const quickActions = [
    { icon: '👑', label: 'Manage Roles', href: '/permission/roles', description: 'Create and edit user roles' },
    { icon: '👥', label: 'User Assignment', href: '/permission/users', description: 'Assign roles to users' },
    { icon: '📊', label: 'Power Analysis', href: '/permission/analysis', description: 'Analyze permission power levels' },
    { icon: '⚡', label: 'Role Templates', href: '/permission/roles/new', description: 'Create roles from templates' }
  ];
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
              <span class="text-lg">{PermissionUtils.getPowerLevelIcon(userMaxPower)}</span>
              <span class="font-semibold text-gray-900">{userPowerLevel}</span>
              <span class="text-sm text-gray-500">({userMaxPower}/100)</span>
            </div>
          </div>
        </div>
      </div>
    </div>

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
            <div class="text-2xl font-bold text-gray-900">{userStats.total_roles}</div>
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
            <div class="text-2xl font-bold text-gray-900">{userStats.total_users}</div>
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
            <div class="text-2xl font-bold text-gray-900">{userStats.total_permissions}</div>
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
            <div class="text-2xl font-bold text-gray-900">{userStats.recent_activity}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="mb-8">
      <h2 class="text-xl font-semibold text-gray-900 mb-4">Quick Actions</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {#each quickActions as action}
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

    <!-- System Roles Overview -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h2 class="text-xl font-semibold text-gray-900 mb-4">System Roles</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {#each [
          { name: 'Basic', power: 10, users: 45, permissions: 8, color: 'green' },
          { name: 'Creator', power: 30, users: 23, permissions: 15, color: 'yellow' },
          { name: 'Moderator', power: 80, users: 8, permissions: 22, color: 'orange' },
          { name: 'Admin', power: 100, users: 3, permissions: 35, color: 'red' }
        ] as role}
          <div class="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors duration-200">
            <div class="flex items-center justify-between mb-2">
              <span class="font-semibold text-gray-900">{role.name}</span>
              <span class="text-sm">{PermissionUtils.getPowerLevelIcon(role.power)}</span>
            </div>
            <div class="space-y-1 text-sm text-gray-600">
              <div>Power: {role.power}/100</div>
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

    <!-- Loading State -->
    {#if $loading.structure}
      <div class="flex justify-center items-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    {/if}
  </div>
</div>