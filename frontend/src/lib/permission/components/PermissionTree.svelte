<script lang="ts">
  import { permissionStructure, treeSelection, permissionActions } from '$lib/stores_permission';
  import { PermissionUtils } from '$lib/utils_permission';
  import { get } from 'svelte/store';
  import type { ModuleDetail, MenuDetail, CardDetail, PermissionDetail } from '$lib/types_permission';

  // Reactive stores
  let searchTerm = '';

  // Handle search
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

  // Selection handlers - FIXED: string-only IDs
  function handleModuleSelection(moduleId: string, event: Event) {
    event.stopPropagation();
    const $permissionStructure = get(permissionStructure);
    if ($permissionStructure) {
      permissionActions.toggleModuleSelectionEnhanced($permissionStructure.modules.find(m => m.id === moduleId));
    }
  }

  function handleMenuSelection(menuId: string, event: Event) {
    event.stopPropagation();
    const $permissionStructure = get(permissionStructure);
    if ($permissionStructure) {
      // Find the menu in the structure
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
    event.stopPropagation();
    const $permissionStructure = get(permissionStructure);
    if ($permissionStructure) {
      // Find the card in the structure
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
    event.stopPropagation();
    permissionActions.togglePermissionSelection(cardId, permissionId);
  }

  // Expand/collapse handlers - FIXED: string-only IDs
  function toggleModule(moduleId: string) {
    permissionActions.toggleNodeExpansion(moduleId);
  }

  function toggleMenu(menuId: string) {
    permissionActions.toggleNodeExpansion(menuId);
  }

  function toggleCard(cardId: string) {
    permissionActions.toggleNodeExpansion(cardId);
  }

  // Auto-expand when searching - FIXED: string-only IDs
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
</script>

<div class="permission-tree">
  <!-- Search Bar -->
  <div class="search-section">
    <input
      type="text"
      bind:value={searchTerm}
      placeholder="Search modules, menus, cards, or permissions..."
      class="search-input"
    />
    <div class="search-actions">
      <button on:click={() => permissionActions.expandAllNodes()} class="btn btn-sm">
        Expand All
      </button>
      <button on:click={() => permissionActions.collapseAllNodes()} class="btn btn-sm">
        Collapse All
      </button>
      <button on:click={() => permissionActions.selectAllPermissions()} class="btn btn-sm">
        Select All
      </button>
      <button on:click={() => permissionActions.clearAllPermissions()} class="btn btn-sm">
        Clear All
      </button>
    </div>
  </div>

  <!-- Tree Structure -->
  <div class="tree-container">
    {#if $permissionStructure}
      {#each $permissionStructure.modules as module (module.id)}
        {#if moduleHasMatches(module, $treeSelection.searchTerm)}
          <!-- MODULE CONTAINER -->
          <div class="module-container tree-node-container">
            <div class="node-header module-header" on:click={() => toggleModule(module.id)}>
              <input
                type="checkbox"
                checked={PermissionUtils.isModuleFullySelected(module.id, $treeSelection.selectedPermissions, $permissionStructure)}
                indeterminate={PermissionUtils.isModulePartiallySelected(module.id, $treeSelection.selectedPermissions, $permissionStructure) && !PermissionUtils.isModuleFullySelected(module.id, $treeSelection.selectedPermissions, $permissionStructure)}
                on:click={handleModuleSelection.bind(null, module.id)}
                on:change={() => {}} <!-- Prevent default behavior -->
              />
              
              <span class="icon">{PermissionUtils.getModuleIcon(module)}</span>
              <span class="name">{module.name}</span>
              <span class="description"> - {module.description}</span>
              
              <span class="expand-icon">
                {$treeSelection.expandedNodes.has(module.id) ? '▼' : '▶'}
              </span>
            </div>

            {#if $treeSelection.expandedNodes.has(module.id)}
              <div class="module-children">
                {#each module.menus as menu (menu.id)}
                  {#if menuHasMatches(menu, $treeSelection.searchTerm)}
                    <!-- MENU CONTAINER -->
                    <div class="menu-container tree-node-container">
                      <div class="node-header menu-header" on:click={() => toggleMenu(menu.id)}>
                        <input
                          type="checkbox"
                          checked={PermissionUtils.isMenuFullySelected(menu.id, $treeSelection.selectedPermissions, $permissionStructure)}
                          indeterminate={PermissionUtils.isMenuPartiallySelected(menu.id, $treeSelection.selectedPermissions, $permissionStructure) && !PermissionUtils.isMenuFullySelected(menu.id, $treeSelection.selectedPermissions, $permissionStructure)}
                          on:click={handleMenuSelection.bind(null, menu.id)}
                          on:change={() => {}} <!-- Prevent default behavior -->
                        />
                        
                        <span class="icon">{PermissionUtils.getMenuIcon(menu)}</span>
                        <span class="name">{menu.name}</span>
                        <span class="description"> - {menu.description}</span>
                        
                        <span class="expand-icon">
                          {$treeSelection.expandedNodes.has(menu.id) ? '▼' : '▶'}
                        </span>
                      </div>

                      {#if $treeSelection.expandedNodes.has(menu.id)}
                        <div class="menu-children">
                          {#each menu.cards as card (card.id)}
                            {#if cardHasMatches(card, $treeSelection.searchTerm)}
                              <!-- CARD CONTAINER -->
                              <div class="card-container tree-node-container">
                                <div class="node-header card-header" on:click={() => toggleCard(card.id)}>
                                  <input
                                    type="checkbox"
                                    checked={PermissionUtils.isCardFullySelected(card.id, $treeSelection.selectedPermissions, $permissionStructure)}
                                    indeterminate={PermissionUtils.isCardPartiallySelected(card.id, $treeSelection.selectedPermissions, $permissionStructure) && !PermissionUtils.isCardFullySelected(card.id, $treeSelection.selectedPermissions, $permissionStructure)}
                                    on:click={handleCardSelection.bind(null, card.id)}
                                    on:change={() => {}} <!-- Prevent default behavior -->
                                  />
                                  
                                  <span class="icon">{PermissionUtils.getCardIcon(card)}</span>
                                  <span class="name">{card.name}</span>
                                  <span class="description"> - {card.description}</span>
                                  
                                  <span class="expand-icon">
                                    {$treeSelection.expandedNodes.has(card.id) ? '▼' : '▶'}
                                  </span>
                                </div>

                                {#if $treeSelection.expandedNodes.has(card.id)}
                                  <div class="card-children permissions-container">
                                    {#each card.permissions as permission (permission.id)}
                                      {#if permissionHasMatches(permission, $treeSelection.searchTerm)}
                                        <div class="permission-node">
                                          <div class="node-header permission-header">
                                            <input
                                              type="checkbox"
                                              checked={PermissionUtils.getCardPermissions(card.id, $treeSelection.selectedPermissions).has(permission.id)}
                                              on:click={handlePermissionSelection.bind(null, card.id, permission.id)}
                                              on:change={() => {}} <!-- Prevent default behavior -->
                                            />
                                            
                                            <span class="icon">{PermissionUtils.getPermissionIcon(permission)}</span>
                                            <span class="name">{permission.display_name}</span>
                                            <span class="description"> - {permission.description}</span>
                                            
                                            <!-- Power Level Badge -->
                                            <span 
                                              class="power-badge {PermissionUtils.getPowerLevelRange(permission.power_level).toLowerCase()}"
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
        {/if}
      {/each}
    {:else}
      <div class="loading-message">Loading permission structure...</div>
    {/if}
  </div>
</div>

<style>
  .permission-tree {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 14px;
    line-height: 1.4;
  }

  /* Search Section */
  .search-section {
    margin-bottom: 16px;
    padding: 12px;
    background: #f8f9fa;
    border-radius: 6px;
    border: 1px solid #e9ecef;
  }

  .search-input {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    margin-bottom: 8px;
    font-size: 14px;
  }

  .search-input:focus {
    outline: none;
    border-color: #007bff;
    box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
  }

  .search-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .btn {
    padding: 6px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    background: white;
    cursor: pointer;
    font-size: 12px;
  }

  .btn:hover {
    background: #f8f9fa;
  }

  .btn-sm {
    padding: 4px 8px;
    font-size: 11px;
  }

  /* Tree Container */
  .tree-container {
    border: 1px solid #e9ecef;
    border-radius: 6px;
    background: white;
    padding: 8px;
  }

  /* CONTAINER STYLES - FIXED */
  .tree-node-container {
    border-radius: 6px;
    margin-bottom: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  .module-container {
    border: 2px solid #007bff !important;
    background: #f0f8ff;
    margin: 12px 0;
  }

  .menu-container {
    border: 2px solid #28a745 !important;
    background: #f0fff0;
    margin: 8px 0;
  }

  .card-container {
    border: 2px solid #ffc107 !important;
    background: #fffbf0;
    margin: 6px 0;
  }

  .permissions-container {
    border: 1px solid #6c757d !important;
    background: #ffffff;
    margin: 4px 0;
    border-radius: 4px;
  }

  /* Children containers - FIXED */
  .module-children {
    padding: 12px;
    background: rgba(255, 255, 255, 0.5);
  }

  .menu-children {
    padding: 10px;
    background: rgba(255, 255, 255, 0.6);
  }

  .card-children {
    padding: 8px;
    background: rgba(255, 255, 255, 0.7);
  }

  /* Node Headers */
  .node-header {
    display: flex;
    align-items: center;
    padding: 12px 16px;
    cursor: pointer;
    user-select: none;
    transition: background-color 0.15s ease;
    border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  }

  .node-header:hover {
    background-color: rgba(0, 0, 0, 0.05);
  }

  .module-header {
    background: #007bff;
    color: white;
    font-weight: 600;
    border-radius: 6px 6px 0 0;
  }

  .menu-header {
    background: #28a745;
    color: white;
    font-weight: 500;
    border-radius: 4px 4px 0 0;
  }

  .menu-header input[type="checkbox"] {
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
  z-index: 10;
  position: relative;
}

  .card-header {
    background: #ffc107;
    color: #212529;
    font-weight: 500;
    border-radius: 4px 4px 0 0;
  }

  .permission-header {
    background: #ffffff;
    cursor: default;
    border-bottom: 1px solid #f8f9fa;
    padding: 8px 16px;
  }

  .permission-header:last-child {
    border-bottom: none;
  }

  /* Checkboxes */
  .node-header input[type="checkbox"] {
    margin-right: 12px;
    cursor: pointer;
    transform: scale(1.2);
  }

  /* Icons and Text */
  .icon {
    margin-right: 12px;
    font-size: 16px;
  }

  .name {
    font-weight: 600;
    margin-right: 8px;
    font-size: 15px;
  }

  .description {
    font-size: 14px;
    flex: 1;
    opacity: 0.9;
  }

  .module-header .description,
  .menu-header .description {
    color: rgba(255, 255, 255, 0.95);
  }

  .expand-icon {
    margin-left: auto;
    font-size: 12px;
    min-width: 16px;
    opacity: 0.9;
  }

  /* Power Badges */
  .power-badge {
    margin-left: 12px;
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    white-space: nowrap;
    border: 1px solid currentColor;
  }

  .power-badge.low {
    background-color: #d4edda;
    color: #155724;
    border-color: #155724;
  }

  .power-badge.medium {
    background-color: #fff3cd;
    color: #856404;
    border-color: #856404;
  }

  .power-badge.high {
    background-color: #ffeaa7;
    color: #e17055;
    border-color: #e17055;
  }

  .power-badge.critical {
    background-color: #f8d7da;
    color: #721c24;
    border-color: #721c24;
  }

  /* Loading State */
  .loading-message {
    padding: 20px;
    text-align: center;
    color: #6c757d;
    font-style: italic;
  }

  /* Indeterminate checkbox styling */
  input[type="checkbox"]:indeterminate {
    background-color: #007bff;
    border-color: #007bff;
  }

  /* Ensure borders are visible */
  .module-container,
  .menu-container,
  .card-container,
  .permissions-container {
    border-style: solid !important;
    border-width: 2px !important;
  }

  /* Responsive Design */
  @media (max-width: 768px) {
    .node-header {
      padding: 10px 12px;
    }
    
    .search-actions {
      flex-direction: column;
    }
    
    .btn {
      width: 100%;
    }
    
    .module-container,
    .menu-container,
    .card-container {
      margin: 8px 0;
    }
    
    .name {
      font-size: 14px;
    }
    
    .description {
      font-size: 13px;
    }
  }
</style>