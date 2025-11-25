  <script>

  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { 
    permissionStructure, 
    treeSelection, 
    loading,
    permissionActions, 
    selectedPermissionIds, 
    selectedPermissionsAnalysis 
  } from '$lib/permission/stores_permission';
  import { PermissionUtils } from '$lib/permission/utils_permission';

  let roleName = $page.params.role;
  let roleData = null;
  let activeTab = 'permissions';
  let saveLoading = false;
  let saveMessage = '';

  // Mock role data based on URL parameter
  const roleMap = {
    basic: {
      name: 'Basic',
      description: 'Basic user with view-only access',
      power_level: 10,
      users: 45,
      permissions: [5001, 5004, 6001, 7001]
    },
    creator: {
      name: 'Creator',
      description: 'Content creator with editing rights', 
      power_level: 30,
      users: 23,
      permissions: [5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 6001, 6002, 6003, 7001, 7002]
    },
    moderator: {
      name: 'Moderator',
      description: 'Content moderator with management tools',
      power_level: 80, 
      users: 8,
      permissions: [5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009, 6001, 6002, 6003, 6004, 8001, 8002, 7001, 7002]
    },
    admin: {
      name: 'Admin',
      description: 'Full system administrator',
      power_level: 100,
      users: 3,
      permissions: [5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009, 5010, 5011, 6001, 6002, 6003, 6004, 6005, 8001, 8002, 8003, 9001, 7001, 7002]
    }
  };

  onMount(() => {
    console.log('inside role');
    console.log($permissionStructure);
    roleData = roleMap[roleName] || roleMap.basic;
    
    // Wait for permission structure to load before initializing selections
    const initializeSelections = () => {
      if ($permissionStructure && roleData) {
        // Clear any existing selections first
        permissionActions.clearAllPermissions();
        
        // Initialize selected permissions for this role
        roleData.permissions.forEach(permId => {
          const perm = PermissionUtils.findPermissionById(permId, $permissionStructure);
          if (perm) {
            const cardId = findCardIdForPermission(permId);
            if (cardId) {
              permissionActions.togglePermissionSelection(cardId, permId);
            }
          }
        });
      } else {
        // If permission structure isn't loaded yet, try again in a moment
        setTimeout(initializeSelections, 100);
      }
    };

    // Start initialization
    initializeSelections();
  });

  function findCardIdForPermission(permissionId) {
    if (!$permissionStructure) return null;
    
    for (const module of $permissionStructure.modules) {
      for (const menu of module.menus) {
        for (const card of menu.cards) {
          for (const permission of card.permissions) {
            if (permission.id === permissionId) {
              return card.id;
            }
          }
        }
      }
    }
    return null;
  }

  async function savePermissions() {
    saveLoading = true;
    saveMessage = '';
    
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      saveMessage = '✅ Permissions updated successfully!';
    } catch (error) {
      saveMessage = '❌ Failed to update permissions';
    } finally {
      saveLoading = false;
    }
  }

  function getFilteredModules() {
    if (!$permissionStructure) return [];
    
    return $permissionStructure.modules.map(module => ({
      ...module,
      menus: module.menus.map(menu => ({
        ...menu,
        cards: menu.cards.map(card => ({
          ...card,
          permissions: card.permissions.filter(perm => 
            !$treeSelection.searchTerm || 
            perm.display_name.toLowerCase().includes($treeSelection.searchTerm.toLowerCase()) ||
            perm.action.toLowerCase().includes($treeSelection.searchTerm.toLowerCase())
          )
        })).filter(card => card.permissions.length > 0)
      })).filter(menu => menu.cards.length > 0)
    })).filter(module => module.menus.length > 0);
  }
</script>

<svelte:head>
  <title>Editing {roleData?.name} - Role Management</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 py-8">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <!-- Header -->
    <div class="mb-8">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-4">
          <a href="/permission/roles" class="text-indigo-600 hover:text-indigo-700">
            ← Back to Roles
          </a>
          <div>
            <h1 class="text-3xl font-bold text-gray-900">Editing Role: {roleData?.name}</h1>
            <p class="mt-2 text-lg text-gray-600">
              {roleData?.description}
            </p>
          </div>
        </div>
        <div class="flex items-center space-x-4">
          <div class="text-right">
            <div class="text-sm text-gray-500">Power Level</div>
            <div class="flex items-center space-x-2">
              <span class="text-2xl">{PermissionUtils.getPowerLevelIcon(roleData?.power_level || 0)}</span>
              <span class="font-semibold text-gray-900">{PermissionUtils.getPowerLevelLabel(roleData?.power_level || 0)}</span>
              <span class="text-sm text-gray-500">({roleData?.power_level || 0}/100)</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="mb-6 border-b border-gray-200">
      <nav class="-mb-px flex space-x-8">
        <button
          class="{activeTab === 'permissions' 
            ? 'border-indigo-500 text-indigo-600' 
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          } whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
          on:click={() => activeTab = 'permissions'}
        >
          🔐 Permissions
        </button>
        <button
          class="{activeTab === 'users' 
            ? 'border-indigo-500 text-indigo-600' 
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          } whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
          on:click={() => activeTab = 'users'}
        >
          👥 Users ({roleData?.users || 0})
        </button>
        <button
          class="{activeTab === 'analysis' 
            ? 'border-indigo-500 text-indigo-600' 
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          } whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
          on:click={() => activeTab = 'analysis'}
        >
          📊 Power Analysis
        </button>
      </nav>
    </div>

    <!-- Permissions Tab -->
    {#if activeTab === 'permissions'}
      <div class="bg-white rounded-lg shadow-sm border border-gray-200">
        <!-- Toolbar -->
        <div class="border-b border-gray-200 p-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-4">
              <!-- Search -->
              <div class="relative">
                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <span class="text-gray-400">🔍</span>
                </div>
                <input
                  type="text"
                  bind:value={$treeSelection.searchTerm}
                  on:input={(e) => permissionActions.setSearchTerm(e.target.value)}
                  placeholder="Search permissions..."
                  class="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 w-64"
                />
              </div>

              <!-- Bulk Actions -->
              <div class="flex items-center space-x-2">
                <button
                  on:click={permissionActions.selectAllPermissions}
                  class="bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-200"
                >
                  Select All
                </button>
                <button
                  on:click={permissionActions.clearAllPermissions}
                  class="bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-200"
                >
                  Clear All
                </button>
                <button
                  on:click={permissionActions.expandAllNodes}
                  class="bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-200"
                >
                  Expand All
                </button>
                <button
                  on:click={permissionActions.collapseAllNodes}
                  class="bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-200"
                >
                  Collapse All
                </button>
              </div>
            </div>

            <div class="text-right">
              <div class="text-sm text-gray-500">Selected Permissions</div>
              <div class="font-semibold text-gray-900">{selectedPermissionIds.length} permissions</div>
            </div>
          </div>
        </div>

        <!-- Permission Tree -->
        <div class="p-6 max-h-96 overflow-y-auto">
          {#if $loading.structure}
            <div class="flex justify-center items-center py-12">
              <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            </div>
          
          {:else if $permissionStructure}
            {#each getFilteredModules() as module}
              <div class="mb-6">
                <!-- Module Header -->
                <div class="flex items-center space-x-3 mb-4 p-3 bg-gray-50 rounded-lg">
                  <button
                    on:click={() => permissionActions.toggleNodeExpansion(module.id)}
                    class="text-gray-500 hover:text-gray-700 transition-colors duration-200"
                  >
                    {#if $treeSelection.expandedNodes.has(module.id)}
                      <span>▼</span>
                    {:else}
                      <span>▶</span>
                    {/if}
                  </button>
                  <span class="text-2xl">{PermissionUtils.getModuleIcon(module)}</span>
                  <div>
                    <h3 class="font-semibold text-gray-900">{module.name}</h3>
                    <p class="text-sm text-gray-500">{module.description}</p>
                  </div>
                </div>

                <!-- Module Content -->
                {#if $treeSelection.expandedNodes.has(module.id)}
                  {#each module.menus as menu}
                    <div class="ml-8 mb-4">
                      <!-- Menu Header -->
                      <div class="flex items-center space-x-3 mb-3 p-2">
                        <button
                          on:click={() => permissionActions.toggleNodeExpansion(menu.id)}
                          class="text-gray-500 hover:text-gray-700 transition-colors duration-200"
                        >
                          {#if $treeSelection.expandedNodes.has(menu.id)}
                            <span>▼</span>
                          {:else}
                            <span>▶</span>
                          {/if}
                        </button>
                        <span class="text-xl">{PermissionUtils.getMenuIcon(menu)}</span>
                        <div>
                          <h4 class="font-medium text-gray-900">{menu.name}</h4>
                          <p class="text-sm text-gray-500">{menu.description}</p>
                        </div>
                      </div>

                      <!-- Menu Content -->
                      {#if $treeSelection.expandedNodes.has(menu.id)}
                        {#each menu.cards as card}
                          <div class="ml-8 mb-4">
                            <!-- Card Header -->
                            <div class="flex items-center space-x-3 mb-3 p-2 bg-white border border-gray-200 rounded-lg">
                              <button
                                on:click={() => permissionActions.toggleNodeExpansion(card.id)}
                                class="text-gray-500 hover:text-gray-700 transition-colors duration-200"
                              >
                                {#if $treeSelection.expandedNodes.has(card.id)}
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
                              <div class="flex items-center space-x-2">
                                <button
                                  on:click={() => permissionActions.selectAllCardPermissions(card.id, card.permissions.map(p => p.id))}
                                  class="text-xs bg-green-100 text-green-700 hover:bg-green-200 px-2 py-1 rounded transition-colors duration-200"
                                >
                                  Select All
                                </button>
                                <button
                                  on:click={() => permissionActions.clearCardPermissions(card.id)}
                                  class="text-xs bg-red-100 text-red-700 hover:bg-red-200 px-2 py-1 rounded transition-colors duration-200"
                                >
                                  Clear
                                </button>
                              </div>
                            </div>

                            <!-- Card Permissions -->
                            {#if $treeSelection.expandedNodes.has(card.id)}
                              <div class="ml-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                                {#each card.permissions as permission}
                                  <div class="flex items-center space-x-3 p-2 bg-gray-50 rounded-lg">
                                    <input
                                      type="checkbox"
                                      checked={$treeSelection.selectedPermissions.get(card.id)?.has(permission.id) || false}
                                      on:change={() => permissionActions.togglePermissionSelection(card.id, permission.id)}
                                      class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                                    />
                                    <span class="text-lg">{PermissionUtils.getPermissionIcon(permission)}</span>
                                    <div class="flex-1">
                                      <div class="font-medium text-gray-900 text-sm">{permission.display_name}</div>
                                      <div class="flex items-center space-x-2 text-xs text-gray-500">
                                        <span>{permission.action}</span>
                                        <span>•</span>
                                        <span class="{
                                          permission.power_level <= 30 ? 'text-green-600' :
                                          permission.power_level <= 60 ? 'text-yellow-600' :
                                          permission.power_level <= 80 ? 'text-orange-600' : 'text-red-600'
                                        }">
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
          {:else}
            <div class="text-center py-12 text-gray-500">
              Failed to load permission structure
              {$permissionStructure}
            </div>
          {/if}
        </div>

        <!-- Footer Actions -->
<div class="border-t border-gray-200 p-4 bg-gray-50 rounded-b-lg">
  <div class="flex items-center justify-between">
    <div class="text-sm text-gray-500">
      {#if $selectedPermissionsAnalysis?.power_distribution}
        Power Distribution: 
        🟢{$selectedPermissionsAnalysis.power_distribution?.low} 
        🟡{$selectedPermissionsAnalysis.power_distribution?.medium} 
        🟠{$selectedPermissionsAnalysis.power_distribution?.high} 
        🔴{$selectedPermissionsAnalysis.power_distribution?.critical}
      {:else}
        Power Distribution: 🟢0 🟡0 🟠0 🔴0
      {/if}
    </div>
    <div class="text-sm text-gray-500">
      Total: {$selectedPermissionIds?.length || 0} permissions selected
    </div>
  </div>
</div>
      </div>
    {/if}

    <!-- Users Tab -->
    {#if activeTab === 'users'}
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div class="text-center py-12">
          <div class="text-gray-400 text-6xl mb-4">👥</div>
          <h3 class="text-lg font-medium text-gray-900 mb-2">User Management</h3>
          <p class="text-gray-500 mb-6">
            Manage users assigned to the {roleData?.name} role
          </p>
          <a
            href="/permission/users?role={roleName}"
            class="bg-indigo-600 text-white hover:bg-indigo-700 px-6 py-3 rounded-lg font-medium transition-colors duration-200 inline-flex items-center space-x-2"
          >
            <span>👥</span>
            <span>Manage Users</span>
          </a>
        </div>
      </div>
    {/if}

    <!-- Analysis Tab -->
    {#if activeTab === 'analysis'}
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div class="text-center py-12">
          <div class="text-gray-400 text-6xl mb-4">📊</div>
          <h3 class="text-lg font-medium text-gray-900 mb-2">Power Analysis</h3>
          <p class="text-gray-500 mb-6">
            Detailed power analysis for the {roleData?.name} role
          </p>
          <a
            href="/permission/analysis/{roleName}"
            class="bg-indigo-600 text-white hover:bg-indigo-700 px-6 py-3 rounded-lg font-medium transition-colors duration-200 inline-flex items-center space-x-2"
          >
            <span>📊</span>
            <span>View Analysis</span>
          </a>
        </div>
      </div>
    {/if}
  </div>
</div>