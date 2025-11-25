<script>
  import { PermissionUtils } from '../utils_permission';
  
  export let role = {
    name: '',
    description: '',
    users: 0,
    permissions: 0,
    power_level: 0,
    is_system_role: false
  };
  
  export let showActions = true;
  export let onEdit = () => {};
  export let onManageUsers = () => {};

  function handleEdit() {
    onEdit(role);
  }

  function handleManageUsers() {
    onManageUsers(role);
  }
</script>

<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow duration-200">
  <!-- Role Header -->
  <div class="flex items-center justify-between mb-4">
    <div class="flex items-center space-x-3">
      <div class="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
        <span class="text-indigo-600 font-semibold">🏷️</span>
      </div>
      <div>
        <h3 class="font-semibold text-gray-900 text-lg">{role.name}</h3>
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
        class="h-2 rounded-full {{
          role.power_level <= 30 ? 'bg-green-500' :
          role.power_level <= 60 ? 'bg-yellow-500' :
          role.power_level <= 80 ? 'bg-orange-500' : 'bg-red-500'
        }}"
        style={`width: ${role.power_level}%`}
      ></div>
    </div>
  </div>

  <!-- Actions -->
  {#if showActions}
    <div class="flex space-x-2">
      <button
        on:click={handleEdit}
        class="flex-1 bg-indigo-600 text-white hover:bg-indigo-700 py-2 px-3 rounded-lg text-sm font-medium text-center transition-colors duration-200"
      >
        Edit Permissions
      </button>
      <button
        on:click={handleManageUsers}
        class="flex-1 bg-gray-100 text-gray-700 hover:bg-gray-200 py-2 px-3 rounded-lg text-sm font-medium text-center transition-colors duration-200"
      >
        Manage Users
      </button>
    </div>
  {/if}
</div>