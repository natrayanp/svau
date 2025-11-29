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
  } from '$lib/permission/stores_permission.ts'; // FIXED IMPORT PATH
  import { PermissionUtils } from '$lib/permission/utils_permission'; // FIXED IMPORT PATH

  let roleName = $page.params.role;
  let roleData = null;
  let activeTab = 'permissions';
  let saveLoading = false;
  let saveMessage = '';
  let initialized = false;

  /* Mock role data based on URL parameter
  const roleMap = {
    basic: {
      name: 'Basic',
      description: 'Basic user with view-only access',
      power_level: 10,
      users: 45,
      permissions: [5001, 5004, 6001, 7001, 8001, 8004]
    },
    creator: {
      name: 'Creator',
      description: 'Content creator with editing rights', 
      power_level: 30,
      users: 23,
      permissions: [5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 6001, 6002, 6003, 7001, 7002, 8001, 8002, 8003, 8004, 8005]
    },
    moderator: {
      name: 'Moderator',
      description: 'Content moderator with management tools',
      power_level: 80, 
      users: 8,
      permissions: [5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009, 6001, 6002, 6003, 6004, 8001, 8002, 8003, 8004, 8005, 8006, 7001, 7002]
    },
    admin: {
      name: 'Admin',
      description: 'Full system administrator',
      power_level: 100,
      users: 3,
      permissions: [5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009, 5010, 5011, 6001, 6002, 6003, 6004, 6005, 8001, 8002, 8003, 8004, 8005, 8006, 8007, 9001, 7001, 7002]
    }
  };
*/
  // Reactive role data
  //$: roleData = roleMap[roleName] || roleMap.basic;


 onMount(() => {
    // Ensure permission structure is loaded
    if (!$permissionStructure) {
      permissionActions.loadPermissionStructure();
    }
      // Load role permissions and ensure permission structure is loaded
    loadRoleData();
  });


async function loadRoleData() {
  try {
    // Ensure permission structure is loaded first
    if (!$permissionStructure) {
      await permissionActions.loadPermissionStructure();
    }
    
    // Load role-specific permissions
    await permissionActions.loadRolePermissions(roleName);
  } catch (err) {
    console.error('Failed to load role data:', err);
  }
}

  /* Initialize selections when permission structure is loaded
  $: {
    if ($permissionStructure && roleData && !initialized) {
      initializeSelections();
      initialized = true;
    }
  }
    */

// Initialize selections when permission structure is loaded
$: {
  if ($permissionStructure && !initialized) {
    // Set initial role data based on URL parameter
    roleData = {
      name: roleName.charAt(0).toUpperCase() + roleName.slice(1),
      description: `${roleName.charAt(0).toUpperCase() + roleName.slice(1)} role with custom permissions`,
      power_level: $selectedPermissionIds.length > 0 ? PermissionUtils.getMaxPower($selectedPermissionIds, $permissionStructure) : 10,
      users: Math.floor(Math.random() * 50) + 1,
      permissions: $selectedPermissionIds
    };
    initialized = true;
  }
}

 
/*
  function initializeSelections() {
    // Clear any existing selections first
    permissionActions.clearAllPermissions();
    
    // Initialize selected permissions for this role
    roleData.permissions.forEach(permId => {
      // This will automatically sync across all locations due to our store logic
      permissionActions.selectPermissionGlobally(permId);
    });
  }*/

  function isModuleSelected(module) {
    const allPermissions = getAllPermissionsInModule(module);
    return allPermissions.every(perm => $selectedPermissionIds.includes(perm.id));
  }

  function isModulePartiallySelected(module) {
    const allPermissions = getAllPermissionsInModule(module);
    const selectedCount = allPermissions.filter(perm => $selectedPermissionIds.includes(perm.id)).length;
    return selectedCount > 0 && selectedCount < allPermissions.length;
  }

  function getAllPermissionsInModule(module) {
    const permissions = [];
    module.menus.forEach(menu => {
      // Add direct menu permissions
      if (menu.permissions) {
        permissions.push(...menu.permissions);
      }
      // Add card permissions
      menu.cards.forEach(card => {
        permissions.push(...card.permissions);
      });
    });
    return permissions;
  }

  function isMenuSelected(menu) {
    const allPermissions = getAllPermissionsInMenu(menu);
    return allPermissions.every(perm => $selectedPermissionIds.includes(perm.id));
  }

  function isMenuPartiallySelected(menu) {
    const allPermissions = getAllPermissionsInMenu(menu);
    const selectedCount = allPermissions.filter(perm => $selectedPermissionIds.includes(perm.id)).length;
    return selectedCount > 0 && selectedCount < allPermissions.length;
  }

  function getAllPermissionsInMenu(menu) {
    const permissions = [];
    // Add direct menu permissions
    if (menu.permissions) {
      permissions.push(...menu.permissions);
    }
    // Add card permissions
    menu.cards.forEach(card => {
      permissions.push(...card.permissions);
    });
    return permissions;
  }

  function isCardSelected(card) {
    return card.permissions.every(perm => $selectedPermissionIds.includes(perm.id));
  }

  function isCardPartiallySelected(card) {
    const selectedCount = card.permissions.filter(perm => $selectedPermissionIds.includes(perm.id)).length;
    return selectedCount > 0 && selectedCount < card.permissions.length;
  }

  function getFilteredModules() {
    if (!$permissionStructure) return [];
    
    return $permissionStructure.modules.map(module => ({
      ...module,
      menus: module.menus.map(menu => ({
        ...menu,
        // Filter cards and their permissions
        cards: menu.cards.map(card => ({
          ...card,
          permissions: card.permissions.filter(perm => 
            !$treeSelection.searchTerm || 
            perm.display_name.toLowerCase().includes($treeSelection.searchTerm.toLowerCase()) ||
            perm.action.toLowerCase().includes($treeSelection.searchTerm.toLowerCase())
          )
        })).filter(card => card.permissions.length > 0),
        // Filter direct menu permissions
        permissions: menu.permissions ? menu.permissions.filter(perm => 
          !$treeSelection.searchTerm || 
          perm.display_name.toLowerCase().includes($treeSelection.searchTerm.toLowerCase()) ||
          perm.action.toLowerCase().includes($treeSelection.searchTerm.toLowerCase())
        ) : []
      })).filter(menu => menu.cards.length > 0 || (menu.permissions && menu.permissions.length > 0))
    })).filter(module => module.menus.length > 0);
  }

  async function savePermissions() {
  saveLoading = true;
  saveMessage = '';
  
  try {
    // Use the actual API method from our store
    const result = await permissionActions.updateRolePermissions(roleName);
    
    if (result.success) {
      saveMessage = '✅ Permissions updated successfully!';
      
      // Update role data with new power level
      if (roleData && $permissionStructure) {
        roleData.power_level = PermissionUtils.getMaxPower($selectedPermissionIds, $permissionStructure);
        roleData.permissions = $selectedPermissionIds;
      }
    } else {
      saveMessage = '❌ Failed to update permissions';
    }
  } catch (error) {
    saveMessage = '❌ Failed to update permissions';
  } finally {
    saveLoading = false;
  }
}

  // Check if a specific permission is selected (works across all locations)
  function isPermissionSelected(permissionId) {
    return $selectedPermissionIds.includes(permissionId);
  }

  // Get power level color with premium styling
  function getPowerLevelColor(level) {
    if (level <= 30) return 'from-emerald-500 to-green-400';
    if (level <= 60) return 'from-amber-500 to-yellow-400';
    if (level <= 80) return 'from-orange-500 to-amber-400';
    return 'from-rose-500 to-red-400';
  }

  function getPowerLevelBg(level) {
    if (level <= 30) return 'bg-gradient-to-r from-emerald-100 to-green-100 text-emerald-800';
    if (level <= 60) return 'bg-gradient-to-r from-amber-100 to-yellow-100 text-amber-800';
    if (level <= 80) return 'bg-gradient-to-r from-orange-100 to-amber-100 text-orange-800';
    return 'bg-gradient-to-r from-rose-100 to-red-100 text-rose-800';
  }
</script>

<svelte:head>
  <title>Editing {roleData?.name} - Role Management</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 py-8">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <!-- Loading State -->
    {#if $loading.structure}
      <div class="flex justify-center items-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        <span class="ml-4 text-gray-600">Loading permission system...</span>
      </div>
    {:else if !$permissionStructure}
      <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
        <div class="text-yellow-800">
          <p class="font-medium">Unable to load permission structure</p>
          <p class="text-sm mt-2">Please check your connection and try again.</p>
          <button 
            on:click={() => permissionActions.loadPermissionStructure()}
            class="mt-4 px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    {:else}
      <!-- Premium Header -->
      <div class="mb-8">
        <div class="bg-white/80 backdrop-blur-xl rounded-2xl shadow-2xl border border-white/20 p-8">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-6">
              <a href="/permission/roles" class="group flex items-center space-x-2 text-slate-600 hover:text-indigo-600 transition-all duration-300">
                <div class="w-8 h-8 bg-white/80 border border-slate-200 rounded-lg flex items-center justify-center group-hover:border-indigo-300 group-hover:bg-indigo-50 transition-all duration-300">
                  <span class="text-lg">←</span>
                </div>
                <span class="font-medium">Back to Roles</span>
              </a>
              <div class="h-8 w-px bg-slate-200"></div>
              <div>
                <h1 class="text-4xl font-bold bg-gradient-to-r from-slate-900 to-slate-700 bg-clip-text text-transparent">
                  Editing Role: {roleData?.name}
                </h1>
                <p class="mt-3 text-lg text-slate-600 font-light">
                  {roleData?.description}
                </p>
              </div>
            </div>
            <div class="text-right">
              <div class="text-sm font-medium text-slate-500 mb-2">Power Level</div>
              <div class="flex items-center space-x-3">
                <div class="relative">
                  <div class="w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                    <span class="text-white font-bold text-lg">{PermissionUtils.getPowerLevelIcon(roleData?.power_level || 0)}</span>
                  </div>
                  <div class="absolute -bottom-1 -right-1 w-6 h-6 bg-white rounded-full border-2 border-white shadow-lg flex items-center justify-center">
                    <div class="w-3 h-3 bg-gradient-to-r {getPowerLevelColor(roleData?.power_level || 0)} rounded-full"></div>
                  </div>
                </div>
                <div>
                  <div class="font-semibold text-slate-900 text-lg">{PermissionUtils.getPowerLevelLabel(roleData?.power_level || 0)}</div>
                  <div class="text-sm text-slate-500">Level {roleData?.power_level || 0}/100</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Premium Tabs -->
      <div class="mb-8">
        <div class="bg-white/80 backdrop-blur-xl rounded-2xl shadow-2xl border border-white/20 p-2">
          <nav class="flex space-x-2">
            <button
              class="flex-1 flex items-center justify-center space-x-3 py-4 px-6 rounded-xl font-semibold text-lg transition-all duration-300 {activeTab === 'permissions' 
                ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/25' 
                : 'text-slate-600 hover:text-slate-800 hover:bg-white/50'
              }"
              on:click={() => activeTab = 'permissions'}
            >
              <span class="text-xl">🔐</span>
              <span>Permissions</span>
            </button>
            <button
              class="flex-1 flex items-center justify-center space-x-3 py-4 px-6 rounded-xl font-semibold text-lg transition-all duration-300 {activeTab === 'users' 
                ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/25' 
                : 'text-slate-600 hover:text-slate-800 hover:bg-white/50'
              }"
              on:click={() => activeTab = 'users'}
            >
              <span class="text-xl">👥</span>
              <span>Users ({roleData?.users || 0})</span>
            </button>
            <button
              class="flex-1 flex items-center justify-center space-x-3 py-4 px-6 rounded-xl font-semibold text-lg transition-all duration-300 {activeTab === 'analysis' 
                ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/25' 
                : 'text-slate-600 hover:text-slate-800 hover:bg-white/50'
              }"
              on:click={() => activeTab = 'analysis'}
            >
              <span class="text-xl">📊</span>
              <span>Power Analysis</span>
            </button>
          </nav>
        </div>
      </div>

      <!-- Permissions Tab -->
      {#if activeTab === 'permissions'}
        <div class="bg-white/80 backdrop-blur-xl rounded-2xl shadow-2xl border border-white/20 overflow-hidden">
          <!-- Premium Toolbar -->
          <div class="border-b border-slate-200/60 p-6 bg-gradient-to-r from-slate-50 to-blue-50/30">
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-4">
                <!-- Premium Search -->
                <div class="relative group">
                  <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <span class="text-slate-400 group-focus-within:text-indigo-500 transition-colors duration-300">🔍</span>
                  </div>
                  <input
                    type="text"
                    bind:value={$treeSelection.searchTerm}
                    placeholder="Search permissions..."
                    class="pl-12 pr-4 py-3 bg-white/80 border border-slate-300/50 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 w-80 shadow-sm transition-all duration-300 focus:shadow-lg focus:shadow-indigo-500/10"
                  />
                </div>

                <!-- Premium Bulk Actions -->
                <div class="flex items-center space-x-2">
                  <button
                    on:click={permissionActions.selectAllPermissions}
                    class="bg-white/80 border border-slate-300/50 text-slate-700 hover:bg-white hover:border-slate-400 hover:text-slate-900 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-300 shadow-sm hover:shadow-md flex items-center space-x-2"
                  >
                    <span>✓</span>
                    <span>Select All</span>
                  </button>
                  <button
                    on:click={permissionActions.clearAllPermissions}
                    class="bg-white/80 border border-slate-300/50 text-slate-700 hover:bg-white hover:border-slate-400 hover:text-slate-900 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-300 shadow-sm hover:shadow-md flex items-center space-x-2"
                  >
                    <span>✕</span>
                    <span>Clear All</span>
                  </button>
                </div>
              </div>

              <div class="text-right">
                <div class="text-sm font-medium text-slate-500 mb-1">Selected Permissions</div>
                <div class="font-bold text-2xl bg-gradient-to-r from-slate-800 to-slate-600 bg-clip-text text-transparent">
                  {$selectedPermissionIds?.length || 0}
                  <span class="text-sm font-normal text-slate-500"> permissions</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Premium Permission Tree -->
          <div class="p-8 max-h-[600px] overflow-y-auto custom-scrollbar">
            {#each getFilteredModules() as module}
              <!-- Premium Module Level -->
              <div class="premium-module-card mb-6">
                <div class="flex items-center space-x-4 p-6">
                  <div class="relative">
                    <input
                      type="checkbox"
                      checked={isModuleSelected(module)}
                      indeterminate={isModulePartiallySelected(module)}
                      on:change={() => permissionActions.toggleModuleSelectionEnhanced(module)}
                      class="premium-checkbox h-5 w-5 text-indigo-600 focus:ring-indigo-500 border-slate-300 rounded-lg"
                    />
                  </div>
                  
                  <button
                    on:click={() => permissionActions.toggleNodeExpansion(module.id)}
                    class="premium-expand-btn text-slate-400 hover:text-indigo-600 transition-all duration-300 transform hover:scale-110"
                  >
                    {#if $treeSelection.expandedNodes.has(module.id)}
                      <span class="text-lg">▼</span>
                    {:else}
                      <span class="text-lg">▶</span>
                    {/if}
                  </button>
                  
                  <div class="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg">
                    <span class="text-white text-2xl">{module.icon}</span>
                  </div>
                  
                  <div class="flex-1">
                    <h3 class="font-bold text-xl text-slate-900">{module.name}</h3>
                    <p class="text-slate-600 mt-1">{module.description}</p>
                  </div>
                </div>

                <!-- Module Content -->
                {#if $treeSelection.expandedNodes.has(module.id)}
                  {#each module.menus as menu}
                    <!-- Premium Menu Level with Combined Border -->
                    <div class="premium-menu-card ml-8 mt-4">
                      <!-- Menu Header -->
                      <div class="flex items-center space-x-4 p-6 border-b border-slate-200/60">
                        <div class="relative">
                          <input
                            type="checkbox"
                            checked={isMenuSelected(menu)}
                            indeterminate={isMenuPartiallySelected(menu)}
                            on:change={() => permissionActions.toggleMenuSelectionEnhanced(menu)}
                            class="premium-checkbox h-5 w-5 text-indigo-600 focus:ring-indigo-500 border-slate-300 rounded-lg"
                          />
                        </div>
                        
                        <button
                          on:click={() => permissionActions.toggleNodeExpansion(menu.id)}
                          class="premium-expand-btn text-slate-400 hover:text-indigo-600 transition-all duration-300 transform hover:scale-110"
                        >
                          {#if $treeSelection.expandedNodes.has(menu.id)}
                            <span class="text-lg">▼</span>
                          {:else}
                            <span class="text-lg">▶</span>
                          {/if}
                        </button>
                        
                        <div class="w-10 h-10 bg-gradient-to-br from-slate-500 to-slate-600 rounded-lg flex items-center justify-center shadow-md">
                          <span class="text-white text-xl">{menu.icon}</span>
                        </div>
                        
                        <div class="flex-1">
                          <h4 class="font-semibold text-lg text-slate-900">{menu.name}</h4>
                          <p class="text-slate-600 text-sm mt-1">{menu.description}</p>
                        </div>
                      </div>

                      <!-- DIRECT MENU PERMISSIONS - Aligned with menu name -->
                      {#if menu.permissions && menu.permissions.length > 0}
                        <div class="p-6">
                          <div class="equal-width-permissions-grid grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {#each menu.permissions as permission}
                              <div class="premium-permission-card group">
                                <div class="flex items-center space-x-4 p-4">
                                  <input
                                    type="checkbox"
                                    checked={isPermissionSelected(permission.id)}
                                    on:change={() => permissionActions.togglePermissionGlobally(permission.id)}
                                    class="premium-checkbox h-5 w-5 text-indigo-600 focus:ring-indigo-500 border-slate-300 rounded-lg flex-shrink-0"
                                  />
                                  <span class="text-2xl flex-shrink-0">{permission.icon}</span>
                                  <div class="flex-1 min-w-0">
                                    <div class="font-semibold text-slate-900 text-sm truncate">{permission.display_name}</div>
                                    <div class="flex items-center justify-between mt-2">
                                      <span class="text-xs text-slate-500 font-medium">{permission.action}</span>
                                      <div class="flex items-center space-x-2">
                                        <div class="w-2 h-2 bg-gradient-to-r {getPowerLevelColor(permission.power_level)} rounded-full"></div>
                                        <span class="text-xs font-bold {getPowerLevelBg(permission.power_level)} px-2 py-1 rounded-full">
                                          {permission.power_level}
                                        </span>
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            {/each}
                          </div>
                        </div>
                      {/if}

                      <!-- CARDS - ONLY SHOWN WHEN MENU IS EXPANDED -->
                      {#if $treeSelection.expandedNodes.has(menu.id)}
                        {#each menu.cards as card}
                          <div class="premium-card-card ml-6 mt-4">
                            <div class="flex items-center space-x-4 p-5">
                              <div class="relative">
                                <input
                                  type="checkbox"
                                  checked={isCardSelected(card)}
                                  indeterminate={isCardPartiallySelected(card)}
                                  on:change={() => permissionActions.toggleCardSelectionEnhanced(card)}
                                  class="premium-checkbox h-5 w-5 text-indigo-600 focus:ring-indigo-500 border-slate-300 rounded-lg"
                                />
                              </div>
                              
                              <button
                                on:click={() => permissionActions.toggleNodeExpansion(card.id)}
                                class="premium-expand-btn text-slate-400 hover:text-indigo-600 transition-all duration-300 transform hover:scale-110"
                              >
                                {#if $treeSelection.expandedNodes.has(card.id)}
                                  <span class="text-lg">▼</span>
                                {:else}
                                  <span class="text-lg">▶</span>
                                {/if}
                              </button>
                              
                              <div class="w-9 h-9 bg-gradient-to-br from-slate-400 to-slate-500 rounded-lg flex items-center justify-center shadow-sm">
                                <span class="text-white text-lg">{card.icon}</span>
                              </div>
                              
                              <div class="flex-1">
                                <h5 class="font-medium text-slate-900">{card.name}</h5>
                                <p class="text-slate-600 text-sm mt-1">{card.description}</p>
                              </div>
                            </div>

                            <!-- Card Permissions - ONLY SHOWN WHEN CARD IS EXPANDED -->
                            {#if $treeSelection.expandedNodes.has(card.id)}
                              <div class="p-5 pt-0">
                                <div class="equal-width-permissions-grid grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                  {#each card.permissions as permission}
                                    <div class="premium-permission-card group">
                                      <div class="flex items-center space-x-4 p-4">
                                        <input
                                          type="checkbox"
                                          checked={isPermissionSelected(permission.id)}
                                          on:change={() => permissionActions.togglePermissionGlobally(permission.id)}
                                          class="premium-checkbox h-5 w-5 text-indigo-600 focus:ring-indigo-500 border-slate-300 rounded-lg flex-shrink-0"
                                        />
                                        <span class="text-2xl flex-shrink-0">{permission.icon}</span>
                                        <div class="flex-1 min-w-0">
                                          <div class="font-semibold text-slate-900 text-sm truncate">{permission.display_name}</div>
                                          <div class="flex items-center justify-between mt-2">
                                            <span class="text-xs text-slate-500 font-medium">{permission.action}</span>
                                            <div class="flex items-center space-x-2">
                                              <div class="w-2 h-2 bg-gradient-to-r {getPowerLevelColor(permission.power_level)} rounded-full"></div>
                                              <span class="text-xs font-bold {getPowerLevelBg(permission.power_level)} px-2 py-1 rounded-full">
                                                {permission.power_level}
                                              </span>
                                            </div>
                                          </div>
                                        </div>
                                      </div>
                                    </div>
                                  {/each}
                                </div>
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
          </div>

          <!-- Premium Footer Actions -->
          <div class="border-t border-slate-200/60 p-6 bg-gradient-to-r from-slate-50 to-blue-50/30">
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-6">
                {#if $selectedPermissionsAnalysis?.power_distribution}
                  <div class="flex items-center space-x-4">
                    <div class="flex items-center space-x-2">
                      <div class="w-3 h-3 bg-emerald-500 rounded-full"></div>
                      <span class="text-sm font-medium text-slate-700">{$selectedPermissionsAnalysis.power_distribution.low} Low</span>
                    </div>
                    <div class="flex items-center space-x-2">
                      <div class="w-3 h-3 bg-amber-500 rounded-full"></div>
                      <span class="text-sm font-medium text-slate-700">{$selectedPermissionsAnalysis.power_distribution.medium} Medium</span>
                    </div>
                    <div class="flex items-center space-x-2">
                      <div class="w-3 h-3 bg-orange-500 rounded-full"></div>
                      <span class="text-sm font-medium text-slate-700">{$selectedPermissionsAnalysis.power_distribution.high} High</span>
                    </div>
                    <div class="flex items-center space-x-2">
                      <div class="w-3 h-3 bg-rose-500 rounded-full"></div>
                      <span class="text-sm font-medium text-slate-700">{$selectedPermissionsAnalysis.power_distribution.critical} Critical</span>
                    </div>
                  </div>
                {:else}
                  <div class="text-sm text-slate-500">No power distribution data available</div>
                {/if}
              </div>
              <div class="flex items-center space-x-4">
                {#if saveMessage}
                  <div class="flex items-center space-x-2 px-4 py-2 rounded-lg {saveMessage.includes('✅') ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}">
                    <span class="text-lg">{saveMessage.includes('✅') ? '✅' : '❌'}</span>
                    <span class="font-medium">{saveMessage}</span>
                  </div>
                {/if}
                <button
                  on:click={savePermissions}
                  disabled={saveLoading}
                  class="premium-save-btn bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 disabled:from-slate-400 disabled:to-slate-500 text-white px-8 py-3 rounded-xl font-semibold transition-all duration-300 shadow-lg hover:shadow-xl hover:scale-105 disabled:shadow-none disabled:scale-100 flex items-center space-x-3"
                >
                  {#if saveLoading}
                    <div class="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
                    <span>Saving...</span>
                  {:else}
                    <span class="text-lg">💾</span>
                    <span>Save Permissions</span>
                  {/if}
                </button>
              </div>
            </div>
          </div>
        </div>
      {/if}

      <!-- Users Tab -->
      {#if activeTab === 'users'}
        <div class="bg-white/80 backdrop-blur-xl rounded-2xl shadow-2xl border border-white/20 p-12">
          <div class="text-center py-12">
            <div class="w-24 h-24 bg-gradient-to-br from-slate-100 to-slate-200 rounded-3xl flex items-center justify-center mx-auto mb-6 shadow-lg">
              <span class="text-4xl">👥</span>
            </div>
            <h3 class="text-2xl font-bold text-slate-900 mb-3">User Management</h3>
            <p class="text-slate-600 text-lg mb-8 max-w-md mx-auto">
              Manage users assigned to the <span class="font-semibold text-slate-900">{roleData?.name}</span> role
            </p>
            <button
              class="premium-action-btn bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white px-8 py-4 rounded-xl font-semibold transition-all duration-300 shadow-lg hover:shadow-xl hover:scale-105 flex items-center space-x-3 mx-auto"
            >
              <span class="text-xl">👥</span>
              <span>Manage Users</span>
            </button>
          </div>
        </div>
      {/if}

      <!-- Analysis Tab -->
      {#if activeTab === 'analysis'}
        <div class="bg-white/80 backdrop-blur-xl rounded-2xl shadow-2xl border border-white/20 p-12">
          <div class="text-center py-12">
            <div class="w-24 h-24 bg-gradient-to-br from-slate-100 to-slate-200 rounded-3xl flex items-center justify-center mx-auto mb-6 shadow-lg">
              <span class="text-4xl">📊</span>
            </div>
            <h3 class="text-2xl font-bold text-slate-900 mb-3">Power Analysis</h3>
            <p class="text-slate-600 text-lg mb-8 max-w-md mx-auto">
              Detailed power analysis for the <span class="font-semibold text-slate-900">{roleData?.name}</span> role
            </p>
            <button
              class="premium-action-btn bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white px-8 py-4 rounded-xl font-semibold transition-all duration-300 shadow-lg hover:shadow-xl hover:scale-105 flex items-center space-x-3 mx-auto"
            >
              <span class="text-xl">📊</span>
              <span>View Analysis</span>
            </button>
          </div>
        </div>
      {/if}
    {/if}
  </div>
</div>


<style>
  /* Premium Custom Styles */
  .premium-module-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(248,250,252,0.9) 100%);
    border: 1px solid rgba(255,255,255,0.8);
    border-radius: 20px;
    box-shadow: 
      0 4px 6px -1px rgba(0, 0, 0, 0.05),
      0 10px 15px -3px rgba(0, 0, 0, 0.05),
      inset 0 1px 0 rgba(255, 255, 255, 0.8);
    backdrop-filter: blur(20px);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .premium-module-card:hover {
    box-shadow: 
      0 20px 25px -5px rgba(0, 0, 0, 0.08),
      0 10px 10px -5px rgba(0, 0, 0, 0.02),
      inset 0 1px 0 rgba(255, 255, 255, 0.8);
    transform: translateY(-2px);
  }

  .premium-menu-card {
    background: rgba(248, 250, 252, 0.8);
    border: 1px solid rgba(226, 232, 240, 0.6);
    border-radius: 16px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03);
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
  }

  .premium-menu-card:hover {
    box-shadow: 0 8px 15px -3px rgba(0, 0, 0, 0.05);
    border-color: rgba(199, 210, 254, 0.5);
  }

  .premium-card-card {
    background: rgba(241, 245, 249, 0.6);
    border: 1px solid rgba(226, 232, 240, 0.4);
    border-radius: 12px;
    transition: all 0.3s ease;
  }

  .premium-card-card:hover {
    background: rgba(248, 250, 252, 0.8);
    border-color: rgba(199, 210, 254, 0.3);
  }

  .premium-permission-card {
    background: white;
    border: 1px solid rgba(226, 232, 240, 0.8);
    border-radius: 12px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
  }

  .premium-permission-card:hover {
    border-color: rgba(165, 180, 252, 0.5);
    box-shadow: 0 4px 12px -2px rgba(99, 102, 241, 0.15);
    transform: translateY(-1px);
  }

  .premium-checkbox {
    border-radius: 8px;
    border: 2px solid #d1d5db;
    transition: all 0.2s ease;
  }

  .premium-checkbox:checked {
    background-color: #4f46e5;
    border-color: #4f46e5;
  }

  .premium-checkbox:indeterminate {
    background-color: #f59e0b;
    border-color: #f59e0b;
  }

  .premium-expand-btn {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
  }

  .premium-expand-btn:hover {
    background: rgba(99, 102, 241, 0.1);
  }

  .premium-save-btn {
    box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.3);
  }

  .premium-action-btn {
    box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.3);
  }

  .custom-scrollbar {
    scrollbar-width: thin;
    scrollbar-color: rgba(156, 163, 175, 0.5) transparent;
  }

  .custom-scrollbar::-webkit-scrollbar {
    width: 6px;
  }

  .custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
    border-radius: 3px;
  }

  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: rgba(156, 163, 175, 0.5);
    border-radius: 3px;
  }

  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: rgba(156, 163, 175, 0.7);
  }

  /* Equal width permissions grid */
  .equal-width-permissions-grid {
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  }

  .equal-width-permissions-grid > * {
    min-height: 80px;
  }

  /* Glass morphism effects */
  .glass {
    background: rgba(255, 255, 255, 0.25);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.18);
  }

  /* Smooth transitions */
  * {
    transition-property: color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter;
    transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
    transition-duration: 150ms;
  }
</style>