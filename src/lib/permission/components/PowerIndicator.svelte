<script>
  import { PermissionUtils } from '../utils_permission';
  
  export let powerLevel = 0;
  export let size = 'md'; // sm, md, lg
  export let showLabel = true;
  export let showValue = false;

  const sizeClasses = {
    sm: 'text-xs',
    md: 'text-sm', 
    lg: 'text-base'
  };
</script>

<div class="inline-flex items-center space-x-1 {sizeClasses[size]}">
  <span class="text-lg">{PermissionUtils.getPowerLevelIcon(powerLevel)}</span>
  
  {#if showLabel}
    <span class="font-medium text-gray-700">{PermissionUtils.getPowerLevelLabel(powerLevel)}</span>
  {/if}
  
  {#if showValue}
    <span class="text-gray-500">({powerLevel}/100)</span>
  {/if}
</div>