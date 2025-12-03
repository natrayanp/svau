<script lang="ts">
  import { permissionStructure, treeSelection, permissionActions } from '$lib/permission/stores_permission';
  import { PermissionUtils } from '$lib/permission/utils_permission';
  import { get } from 'svelte/store';
  import type { ModuleDetail, MenuDetail, CardDetail, PermissionDetail } from '$lib/types_permission';

  // Export props for customization
  export let isViewMode = false;

  // Reactive stores
  let searchTerm = '';

  // Handle search - available in both modes
  $: {
    if (searchTerm !== $treeSelection.searchTerm) {
      permissionActions.setSearchTerm(searchTerm);
    }
  }

  // Filter function
  function filterItems<T extends { name: string; description: string }>(
    items: T[],
    term: string
  ): T[] {
    if (!term) return items;
    const lowerTerm = term.toLowerCase();
    return items.filter(item => 
      item.name.toLowerCase().includes(lowerTerm) ||
      item.description.toLowerCase().includes(lowerTerm)
    );
  }

  // Check if module has matching content
  function moduleHasMatches(module: ModuleDetail, term: string): boolean {
    if (!term) return true;
    const lowerTerm = term.toLowerCase();
    
    if (
      module.name.toLowerCase().includes(lowerTerm) ||
      module.description.toLowerCase().includes(lowerTerm)
    ) return true;

    return module.menus.some(menu => 
      menuHasMatches(menu, term)
    );
  }

  // Check if menu has matching content
  function menuHasMatches(menu: MenuDetail, term: string): boolean {
    if (!term) return true;
    const lowerTerm = term.toLowerCase();
    
    if (
      menu.name.toLowerCase().includes(lowerTerm) ||
      menu.description.toLowerCase().includes(lowerTerm)
    ) return true;

    return menu.cards.some(card => 
      cardHasMatches(card, term)
    );
  }

  // Check if card has matching content
  function cardHasMatches(card: CardDetail, term: string): boolean {
    if (!term) return true;
    const lowerTerm = term.toLowerCase();
    
    if (
      card.name.toLowerCase().includes(lowerTerm) ||
      card.description.toLowerCase().includes(lowerTerm)
    ) return true;

    return card.permissions.some(permission => 
      permissionHasMatches(permission, term)
    );
  }

  // Check if permission has matching content
  function permissionHasMatches(permission: PermissionDetail, term: string): boolean {
    if (!term) return true;
    const lowerTerm = term.toLowerCase();
    
    return (
      permission.display_name.toLowerCase().includes(lowerTerm) ||
      permission.description.toLowerCase().includes(lowerTerm) ||
      permission.permission_action.toLowerCase().includes(lowerTerm)
    );
  }

  // Get module card count for badge
  function getModuleCardCount(module: ModuleDetail): { current: number; total: number } {
    const $permissionStructure = get(permissionStructure);
    const $treeSelection = get(treeSelection);
    
    if (!$permissionStructure) return { current: 0, total: 0 };

    let totalCards = 0;
    let currentCardNumber = 0;

    // Count cards in this module and find current position
    $permissionStructure.modules.forEach((mod, modIndex) => {
      mod.menus.forEach(menu => {
        menu.cards.forEach(card => {
          totalCards++;
          // Check if this is the current module and count cards before current position
          if (mod.id === module.id) {
            currentCardNumber++;
          }
        });
      });
    });

    return { current: currentCardNumber, total: totalCards };
  }

  // Selection handlers - disabled in view mode
  function handleModuleSelection(moduleId: string, event: Event) {
    if (isViewMode) return;
    event.stopPropagation();
    const $permissionStructure = get(permissionStructure);
    if ($permissionStructure) {
      permissionActions.toggleModuleSelectionEnhanced($permissionStructure.modules.find(m => m.id === moduleId));
    }
  }

  function handleMenuSelection(menuId: string, event: Event) {
    if (isViewMode) return;
    event.stopPropagation();
    const $permissionStructure = get(permissionStructure);
    if ($permissionStructure) {
      for (const module of $permissionStructure.modules) {
        const menu = module.menus.find(m => m.id === menuId);
        if (menu) {
          permissionActions.toggleMenuSelectionEnhanced(menu);
          break;
        }
      }
    }
  }

  function handleCardSelection(cardId: string, event: Event) {
    if (isViewMode) return;
    event.stopPropagation();
    const $permissionStructure = get(permissionStructure);
    if ($permissionStructure) {
      for (const module of $permissionStructure.modules) {
        for (const menu of module.menus) {
          const card = menu.cards.find(c => c.id === cardId);
          if (card) {
            permissionActions.toggleCardSelectionEnhanced(card);
            break;
          }
        }
      }
    }
  }

  function handlePermissionSelection(cardId: string, permissionId: string, event: Event) {
    if (isViewMode) return;
    event.stopPropagation();
    permissionActions.togglePermissionSelection(cardId, permissionId);
  }

  // Expand/collapse handlers - available in both modes
  function toggleModule(moduleId: string) {
    permissionActions.toggleNodeExpansion(moduleId);
  }

  function toggleMenu(menuId: string) {
    permissionActions.toggleNodeExpansion(menuId);
  }

  function toggleCard(cardId: string) {
    permissionActions.toggleNodeExpansion(cardId);
  }

  // Auto-expand when searching - available in both modes
  $: {
    if ($treeSelection.searchTerm) {
      const $permissionStructure = get(permissionStructure);
      if ($permissionStructure) {
        const nodesToExpand = new Set<string>();
        
        $permissionStructure.modules.forEach(module => {
          if (moduleHasMatches(module, $treeSelection.searchTerm)) {
            nodesToExpand.add(module.id);
            module.menus.forEach(menu => {
              if (menuHasMatches(menu, $treeSelection.searchTerm)) {
                nodesToExpand.add(menu.id);
                menu.cards.forEach(card => {
                  if (cardHasMatches(card, $treeSelection.searchTerm)) {
                    nodesToExpand.add(card.id);
                  }
                });
              }
            });
          }
        });
        
        treeSelection.update(ts => ({ ...ts, expandedNodes: nodesToExpand }));
      }
    }
  }

  // Helper function for power badge classes
  function getPowerBadgeClass(powerLevel: number): string {
    if (powerLevel <= 25) return 'bg-green-100 text-green-800 border-green-800';
    if (powerLevel <= 50) return 'bg-yellow-100 text-yellow-800 border-yellow-800';
    if (powerLevel <= 75) return 'bg-orange-100 text-orange-800 border-orange-800';
    return 'bg-red-100 text-red-800 border-red-800';
  }
</script>

<div class="permission-tree bg-white rounded-lg shadow-sm {isViewMode ? 'opacity-95' : ''}">
  <!-- Search Section - Available in both modes -->
  <div class="search-section bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4">
    <input
      type="text"
      bind:value={searchTerm}
      placeholder="Search modules, menus, cards, or permissions..."
      class="search-input w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent mb-3"
    />
    <div class="search-actions flex flex-wrap gap-2">
      <!-- Expand/Collapse actions - available in both modes -->
      <button 
        on:click={() => permissionActions.expandAllNodes()} 
        class="btn bg-white border border-gray-300 rounded px-3 py-1 text-sm hover:bg-gray-50 transition-colors"
      >
        Expand All
      </button>
      <button 
        on:click={() => permissionActions.collapseAllNodes()} 
        class="btn bg-white border border-gray-300 rounded px-3 py-1 text-sm hover:bg-gray-50 transition-colors"
      >
        Collapse All
      </button>
      
      <!-- Selection actions - only in edit mode -->
      {#if !isViewMode}
        <button 
          on:click={() => permissionActions.selectAllPermissions()} 
          class="btn bg-white border border-gray-300 rounded px-3 py-1 text-sm hover:bg-gray-50 transition-colors"
        >
          Select All
        </button>
        <button 
          on:click={() => permissionActions.clearAllPermissions()} 
          class="btn bg-white border border-gray-300 rounded px-3 py-1 text-sm hover:bg-gray-50 transition-colors"
        >
          Clear All
        </button>
      {/if}
    </div>
  </div>

  <!-- Tree Structure -->
  <div class="tree-container border border-gray-200 rounded-lg bg-white p-4">
    {#if $permissionStructure}
      <!-- View Mode Banner -->
      {#if isViewMode}
        <div class="view-mode-banner bg-blue-50 border border-blue-200 rounded-md p-3 mb-4 text-center">
          <p class="text-blue-700 font-medium text-sm">
            👁️ View Mode - Permissions are read-only
          </p>
        </div>
      {/if}

      <!-- Grid container for responsive layout -->
      <div class="modules-grid grid grid-cols-1 xl:grid-cols-2 gap-6 lg:gap-8 items-start">
        {#each $permissionStructure.modules as module (module.id)}
          {#if moduleHasMatches(module, $treeSelection.searchTerm)}
            <!-- MODULE CONTAINER with Count Badge -->
            <div class="module-wrapper relative">
              <!-- Count Badge - Positioned outside at top-left corner -->
              <div class="count-badge absolute -top-2 -left-2 bg-blue-600 text-white rounded-full w-12 h-6 flex items-center justify-center text-xs font-bold shadow-lg border-2 border-white z-10">
                {getModuleCardCount(module).current}/{getModuleCardCount(module).total}
              </div>
              
              <div class="module-container bg-blue-50 border-2 border-blue-500 rounded-lg shadow-sm {isViewMode ? '' : 'hover:shadow-md transition-all duration-300 hover:-translate-y-1'} h-fit ml-2 mt-2">
                <div
                  role="button"
                  tabindex="0"
                  class="node-header module-header bg-blue-600 text-white px-4 py-3 rounded-t-lg cursor-pointer select-none {isViewMode ? 'hover:bg-blue-600' : 'hover:bg-blue-700'} transition-colors flex items-center gap-3"
                  on:click={() => toggleModule(module.id)}
                  on:keydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleModule(module.id); } }}
                >
                  <!-- Checkbox - Disabled in view mode -->
                  <input
                    type="checkbox"
                    class="h-4 w-4 {isViewMode ? 'cursor-default opacity-70' : 'cursor-pointer'}"
                    checked={PermissionUtils.isModuleFullySelected(module.id, $treeSelection.selectedPermissions, $permissionStructure)}
                    indeterminate={PermissionUtils.isModulePartiallySelected(module.id, $treeSelection.selectedPermissions, $permissionStructure) && !PermissionUtils.isModuleFullySelected(module.id, $treeSelection.selectedPermissions, $permissionStructure)}
                    on:click={handleModuleSelection.bind(null, module.id)}
                    on:change={() => {}}
                    disabled={isViewMode}
                  />
                  
                  <span class="icon text-lg">{PermissionUtils.getModuleIcon(module)}</span>
                  <span class="name font-semibold text-sm">{module.name}</span>
                  <span class="description text-blue-100 text-sm flex-1"> - {module.description}</span>
                  
                  <span class="expand-icon text-xs opacity-90">
                    {$treeSelection.expandedNodes.has(module.id) ? '▼' : '▶'}
                  </span>
                </div>

                {#if $treeSelection.expandedNodes.has(module.id)}
                  <div class="module-children p-4 bg-white/50 rounded-b-lg space-y-3">
                    {#each module.menus as menu (menu.id)}
                      {#if menuHasMatches(menu, $treeSelection.searchTerm)}
                        <!-- MENU CONTAINER -->
                        <div class="menu-container bg-green-50 border-2 border-green-500 rounded-lg shadow-sm {isViewMode ? '' : 'transition-all duration-200'}">
                          <div 
                            class="node-header menu-header bg-green-600 text-white px-4 py-3 rounded-t-lg cursor-pointer select-none {isViewMode ? 'hover:bg-green-600' : 'hover:bg-green-700'} transition-colors flex items-center gap-3"
                            on:click={() => toggleMenu(menu.id)}
                          >
                            <!-- Checkbox - Disabled in view mode -->
                            <input
                              type="checkbox"
                              class="h-4 w-4 {isViewMode ? 'cursor-default opacity-70' : 'cursor-pointer'}"
                              checked={PermissionUtils.isMenuFullySelected(menu.id, $treeSelection.selectedPermissions, $permissionStructure)}
                              indeterminate={PermissionUtils.isMenuPartiallySelected(menu.id, $treeSelection.selectedPermissions, $permissionStructure) && !PermissionUtils.isMenuFullySelected(menu.id, $treeSelection.selectedPermissions, $permissionStructure)}
                              on:click={handleMenuSelection.bind(null, menu.id)}
                              on:change={() => {}}
                              disabled={isViewMode}
                            />
                            
                            <span class="icon text-lg">{PermissionUtils.getMenuIcon(menu)}</span>
                            <span class="name font-semibold text-sm">{menu.name}</span>
                            <span class="description text-green-100 text-sm flex-1 min-w-0"> - {menu.description}</span>
                            
                            <span class="expand-icon text-xs opacity-90">
                              {$treeSelection.expandedNodes.has(menu.id) ? '▼' : '▶'}
                            </span>
                          </div>

                          {#if $treeSelection.expandedNodes.has(menu.id)}
                            <div class="menu-children p-3 bg-white/60 rounded-b-lg space-y-2">
                              {#each menu.cards as card (card.id)}
                                {#if cardHasMatches(card, $treeSelection.searchTerm)}
                                  <!-- CARD CONTAINER -->
                                  <div class="card-container bg-yellow-50 border-2 border-yellow-500 rounded-lg shadow-sm {isViewMode ? '' : 'transition-all duration-200'}">
                                    <div 
                                      class="node-header card-header bg-yellow-500 text-gray-900 px-4 py-2 rounded-t-lg cursor-pointer select-none {isViewMode ? 'hover:bg-yellow-500' : 'hover:bg-yellow-600'} transition-colors flex items-center gap-3"
                                      on:click={() => toggleCard(card.id)}
                                    >
                                      <!-- Checkbox - Disabled in view mode -->
                                      <input
                                        type="checkbox"
                                        class="h-4 w-4 {isViewMode ? 'cursor-default opacity-70' : 'cursor-pointer'}"
                                        checked={PermissionUtils.isCardFullySelected(card.id, $treeSelection.selectedPermissions, $permissionStructure)}
                                        indeterminate={PermissionUtils.isCardPartiallySelected(card.id, $treeSelection.selectedPermissions, $permissionStructure) && !PermissionUtils.isCardFullySelected(card.id, $treeSelection.selectedPermissions, $permissionStructure)}
                                        on:click={handleCardSelection.bind(null, card.id)}
                                        on:change={() => {}}
                                        disabled={isViewMode}
                                      />
                                      
                                      <span class="icon text-lg">{PermissionUtils.getCardIcon(card)}</span>
                                      <span class="name font-semibold text-sm">{card.name}</span>
                                      <span class="description text-gray-700 text-sm flex-1 min-w-0"> - {card.description}</span>
                                      
                                      <span class="expand-icon text-xs opacity-90">
                                        {$treeSelection.expandedNodes.has(card.id) ? '▼' : '▶'}
                                      </span>
                                    </div>

                                    {#if $treeSelection.expandedNodes.has(card.id)}
                                      <div class="card-children permissions-container bg-white border border-gray-400 rounded-b-lg p-2 space-y-1">
                                        {#each card.permissions as permission (permission.id)}
                                          {#if permissionHasMatches(permission, $treeSelection.searchTerm)}
                                            <div class="permission-node bg-white border-b border-gray-100 last:border-b-0">
                                              <div class="node-header permission-header px-3 py-2 flex items-center gap-3 {isViewMode ? '' : 'hover:bg-gray-50'} transition-colors">
                                                <!-- Checkbox - Disabled in view mode -->
                                                <input
                                                  type="checkbox"
                                                  class="h-4 w-4 {isViewMode ? 'cursor-default opacity-70' : 'cursor-pointer'}"
                                                  checked={PermissionUtils.getCardPermissions(card.id, $treeSelection.selectedPermissions).has(permission.id)}
                                                  on:click={handlePermissionSelection.bind(null, card.id, permission.id)}
                                                  on:change={() => {}}
                                                  disabled={isViewMode}
                                                />
                                                
                                                <span class="icon text-base">{PermissionUtils.getPermissionIcon(permission)}</span>
                                                <span class="name font-medium text-sm">{permission.display_name}</span>
                                                <span class="description text-gray-600 text-sm flex-1 min-w-0"> - {permission.description}</span>
                                                
                                                <!-- Power Level Badge -->
                                                <span 
                                                  class="power-badge px-2 py-1 rounded-full text-xs font-semibold border whitespace-nowrap {getPowerBadgeClass(permission.power_level)}"
                                                  title="Power Level: {permission.power_level}"
                                                >
                                                  {PermissionUtils.getPowerLevelIcon(permission.power_level)}
                                                  {permission.power_level}
                                                </span>
                                              </div>
                                            </div>
                                          {/if}
                                        {/each}
                                      </div>
                                    {/if}
                                  </div>
                                {/if}
                              {/each}
                            </div>
                          {/if}
                        </div>
                      {/if}
                    {/each}
                  </div>
                {/if}
              </div>
            </div>
          {/if}
        {/each}
      </div>
    {:else}
      <div class="loading-message text-gray-500 text-center py-5 italic">
        Loading permission structure...
      </div>
    {/if}
  </div>
</div>

<style>
  /* Custom styles for indeterminate checkboxes */
  input[type="checkbox"]:indeterminate {
    background-color: #007bff;
    border-color: #007bff;
  }

  /* Focus states for accessibility */
  .node-header:focus {
    outline: 2px solid #007bff;
    outline-offset: 2px;
  }

  input[type="checkbox"]:focus {
    outline: 2px solid #007bff;
    outline-offset: 2px;
  }

  /* Smooth animations */
  .module-container,
  .menu-container,
  .card-container {
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }

  /* View mode specific styles */
  .view-mode-banner {
    border-left: 4px solid #3b82f6;
  }

  /* Disabled checkbox styling */
  input[type="checkbox"]:disabled {
    cursor: default;
  }

  input[type="checkbox"]:disabled:checked {
    background-color: #6b7280;
    border-color: #6b7280;
  }

  input[type="checkbox"]:disabled:indeterminate {
    background-color: #6b7280;
    border-color: #6b7280;
  }

  /* Count badge styling */
  .count-badge {
    font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Monaco, Consolas, monospace;
    min-width: 3rem;
  }

  /* Ensure proper z-index for badges */
  .module-wrapper {
    z-index: 1;
  }

  .count-badge {
    z-index: 20;
  }
</style>