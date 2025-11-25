<script>
  import { PermissionUtils } from '../utils_permission';
  
  export let modules = [];
  export let selectedPermissions = new Map();
  export let expandedNodes = new Set();
  export let searchTerm = '';
  export let onPermissionToggle = (cardId, permissionId) => {};
  export let onNodeToggle = (nodeId) => {};

  function handlePermissionToggle(cardId, permissionId) {
    onPermissionToggle(cardId, permissionId);
  }

  function handleNodeToggle(nodeId) {
    onNodeToggle(nodeId);
  }

  function getFilteredModules() {
    if (!searchTerm.trim()) return modules;
    
    return modules.map(module => ({
      ...module,
      menus: module.menus.map(menu => ({
        ...menu,
        cards: menu.cards.map(card => ({
          ...card,
          permissions: card.permissions.filter(perm => 
            perm.display_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            perm.action.toLowerCase().includes(searchTerm.toLowerCase())
          )
        })).filter(card => card.permissions.length > 0)
      })).filter(menu => menu.cards.length > 0)
    })).filter(module => module.menus.length > 0);
  }
</script>

<div class="permission-tree">
  {#each getFilteredModules() as module}
    <div class="module-section mb-6">
      <!-- Module Header -->
      <div class="flex items-center space-x-3 mb-4 p-3 bg-gray-50 rounded-lg">
        <button
          on:click={() => handleNodeToggle(module.id)}
          class="text-gray-500 hover:text-gray-700 transition-colors duration-200"
        >
          {#if expandedNodes.has(module.id)}
            <span>▼</span>
          {:else}
            <span>▶</span>
          {/if}
        </button>
        <span class="text-2xl">{PermissionUtils.getModuleIcon(module)}</span>
        <div class="flex-1">
          <h3 class="font-semibold text-gray-900">{module.name}</h3>
          <p class="text-sm text-gray-500">{module.description}</p>
        </div>
      </div>

      <!-- Module Content -->
      {#if expandedNodes.has(module.id)}
        {#each module.menus as menu}
          <div class="menu-section ml-8 mb-4">
            <!-- Menu Header -->
            <div class="flex items-center space-x-3 mb-3 p-2">
              <button
                on:click={() => handleNodeToggle(menu.id)}
                class="text-gray-500 hover:text-gray-700 transition-colors duration-200"
              >
                {#if expandedNodes.has(menu.id)}
                  <span>▼</span>
                {:else}
                  <span>▶</span>
                {/if}
              </button>
              <span class="text-xl">{PermissionUtils.getMenuIcon(menu)}</span>
              <div class="flex-1">
                <h4 class="font-medium text-gray-900">{menu.name}</h4>
                <p class="text-sm text-gray-500">{menu.description}</p>
              </div>
            </div>

            <!-- Menu Content -->
            {#if expandedNodes.has(menu.id)}
              {#each menu.cards as card}
                <div class="card-section ml-8 mb-4">
                  <!-- Card Header -->
                  <div class="flex items-center space-x-3 mb-3 p-3 bg-white border border-gray-200 rounded-lg">
                    <button
                      on:click={() => handleNodeToggle(card.id)}
                      class="text-gray-500 hover:text-gray-700 transition-colors duration-200"
                    >
                      {#if expandedNodes.has(card.id)}
                        <span>▼</span>
                      {:else}
                        <span>▶</span>
                      {/if}
                    </button>
                    <span class="text-lg">{PermissionUtils.getCardIcon(card)}</span>
                    <div class="flex-1">
                      <h5 class="font-medium text-gray-900">{card.name}</h5>
                      <p class="text-sm text-gray-500">{card.description}</p>
                    </div>
                    <div class="text-sm text-gray-500">
                      {selectedPermissions.get(card.id)?.size || 0}/{card.permissions.length} selected
                    </div>
                  </div>

                  <!-- Card Permissions -->
                  {#if expandedNodes.has(card.id)}
                    <div class="permissions-grid ml-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                      {#each card.permissions as permission}
                        <div class="permission-item flex items-center space-x-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors duration-150">
                          <input
                            type="checkbox"
                            checked={selectedPermissions.get(card.id)?.has(permission.id) || false}
                            on:change={() => handlePermissionToggle(card.id, permission.id)}
                            class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                          />
                          <span class="text-lg">{PermissionUtils.getPermissionIcon(permission)}</span>
                          <div class="flex-1">
                            <div class="font-medium text-gray-900 text-sm">{permission.display_name}</div>
                            <div class="flex items-center space-x-2 text-xs text-gray-500">
                              <span>{permission.action}</span>
                              <span>•</span>
                              <span class="{{
                                permission.power_level <= 30 ? 'text-green-600' :
                                permission.power_level <= 60 ? 'text-yellow-600' :
                                permission.power_level <= 80 ? 'text-orange-600' : 'text-red-600'
                              }}">
                                Power {permission.power_level}
                              </span>
                            </div>
                          </div>
                        </div>
                      {/each}
                    </div>
                  {/if}
                </div>
              {/each}
            {/if}
          </div>
        {/each}
      {/if}
    </div>
  {/each}

  <!-- Empty State -->
  {#if getFilteredModules().length === 0}
    <div class="text-center py-12 text-gray-500">
      <div class="text-4xl mb-4">🔍</div>
      <p>No permissions found matching your search</p>
    </div>
  {/if}
</div>

<style>
  .permission-tree {
    max-height: 600px;
    overflow-y: auto;
  }
  
  .module-section, .menu-section, .card-section {
    transition: all 0.2s ease-in-out;
  }
</style>