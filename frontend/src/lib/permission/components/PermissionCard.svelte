<script>
  import { PermissionUtils } from '../utils_permission';
  
  export let permission = {
    id: 0,
    action: '',
    display_name: '',
    description: '',
    power_level: 0,
    default_roles: []
  };
  
  export let checked = false;
  export let showCheckbox = true;
  export let onToggle = () => {};

  function handleToggle() {
    onToggle(permission.id);
  }

  function getPowerColor(power) {
    return power <= 30 ? 'green' :
           power <= 60 ? 'yellow' :
           power <= 80 ? 'orange' : 'red';
  }
</script>

<div class="permission-card flex items-center space-x-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors duration-150 border border-gray-200">
  {#if showCheckbox}
    <input
      type="checkbox"
      {checked}
      on:change={handleToggle}
      class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
    />
  {/if}
  
  <span class="text-lg">{PermissionUtils.getPermissionIcon(permission)}</span>
  
  <div class="flex-1">
    <div class="font-medium text-gray-900 text-sm">{permission.display_name}</div>
    <div class="text-xs text-gray-500">{permission.description}</div>
    <div class="flex items-center space-x-3 mt-1 text-xs text-gray-600">
      <span>Action: {permission.action}</span>
      <span>•</span>
      <span class="font-medium text-{getPowerColor(permission.power_level)}-600">
        Power {permission.power_level}
      </span>
      {#if permission.default_roles.length > 0}
        <span>•</span>
        <span>Default: {permission.default_roles.join(', ')}</span>
      {/if}
    </div>
  </div>
  
  <!-- Power Indicator -->
  <div class="text-right">
    <div class="text-lg">{PermissionUtils.getPowerLevelIcon(permission.power_level)}</div>
    <div class="text-xs text-gray-500">{PermissionUtils.getPowerLevelLabel(permission.power_level)}</div>
  </div>
</div>

<style>
  .permission-card {
    min-height: 80px;
  }
</style>