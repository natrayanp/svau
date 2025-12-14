<script lang="ts">
	import { onMount } from 'svelte';
	import { permissionStructureStore } from '$lib/permission/stores/permission_readonly_stores';
	import type { ModuleDetail, MenuDetail, CardDetail, AllowedAction } from '$lib/types_permission';

	import type { RolePermissions } from '$lib/permission/stores/types_permission';

	// Props
	export let isViewMode = false;
	export let selectedPermissions: { permissstruct_id: string; granted_action_key: string[] }[] = [];
	export const originalPermissions: { permissstruct_id: string; granted_action_key: string[] }[] = [];
	export let onPermissionsChange: (
		p: { permissstruct_id: string; granted_action_key: string[] }[]
	) => void = () => {};

	export let viewActionPatterns: string[] = ['view', 'access', 'read'];
	export let viewMatchProperty: string = 'action_key';

	// Store destructuring
	const { data: permissionStructureData, loading: permissionStructureLoading } =
		permissionStructureStore;

	// Local state
	let searchTerm = '';
	let expandedNodes = new Set<string>();
	let localSelectedPermissions = [...selectedPermissions];
	let hasInitialized = false;

	// Reactive store extraction
	$: permissionData = $permissionStructureData;
	$: loading = $permissionStructureLoading;
	$: updateTrigger = 0;

	// Update local selection when props change
	$: {
		// Ensure we sync if prop changes and differs from local
		// Simple length check + crude stringify to avoid deep comparison overhead on every render
		const propStr = JSON.stringify(selectedPermissions); // efficient enough for small-medium objects
		const localStr = JSON.stringify(localSelectedPermissions);

		if (propStr !== localStr) {
			console.log('PermissionTree: detecting prop change', {
				prop: selectedPermissions.length,
				local: localSelectedPermissions.length
			});
			// If not initialized, definitely take it.
			// If initialized, but prop changed significantly (parent update), take it?
			// To avoid loops (child -> parent -> child), we need to know if parent update was caused by child.
			// But here, usually parent updates only on load.
			// Let's rely on hasInitialized primarily for initial load, BUT also allow override if prop changes length from 0 to something (delayed load).

			if (
				!hasInitialized ||
				(localSelectedPermissions.length === 0 && selectedPermissions.length > 0)
			) {
				console.log('PermissionTree: Syncing from props', selectedPermissions);
				localSelectedPermissions = [...selectedPermissions];
				if (selectedPermissions.length > 0) hasInitialized = true;
			}
		}
	}

	// Load permissions on mount
	onMount(async () => {
		console.log('selectedPermissions');
		console.log(selectedPermissions);
		if (!$permissionStructureData && !$permissionStructureLoading) {
			await permissionStructureStore.load();
		}
	});

	// ------------------------------
	// HELPER FUNCTIONS
	// ------------------------------

	function isViewAction(action: AllowedAction): boolean {
		if (action.category === 'access') return true;
		const fieldValue = (action as any)[viewMatchProperty];
		return (
			typeof fieldValue === 'string' &&
			viewActionPatterns.some((pattern) => fieldValue.toLowerCase().includes(pattern.toLowerCase()))
		);
	}

	// Check if a specific action is granted for a structure
	function isActionGranted(structureId: string, actionKey: string, _dep?: any): boolean {
		const structure = localSelectedPermissions.find(
			(item) => item.permissstruct_id === structureId
		);
		return structure ? structure.granted_action_key.includes(actionKey) : false;
	}

	// Get all granted actions for a structure
	function getGrantedActions(structureId: string): string[] {
		const structure = localSelectedPermissions.find(
			(item) => item.permissstruct_id === structureId
		);
		return structure ? structure.granted_action_key : [];
	}

	// Get all possible action keys for a structure
	function getAllActionKeysForStructure(
		structure: ModuleDetail | MenuDetail | CardDetail
	): string[] {
		return structure.allowed_actions?.map((action) => action.action_key) || [];
	}

	// Update permission for a structure
	function updateStructurePermission(structureId: string, actionKeys: string[]) {
		const newPermissions = [...localSelectedPermissions];
		const existingIndex = newPermissions.findIndex((item) => item.permissstruct_id === structureId);

		if (actionKeys.length > 0) {
			// Update or add structure with actions
			if (existingIndex >= 0) {
				newPermissions[existingIndex] = {
					permissstruct_id: structureId,
					granted_action_key: actionKeys
				};
			} else {
				newPermissions.push({
					permissstruct_id: structureId,
					granted_action_key: actionKeys
				});
			}
		} else {
			// Remove structure if no actions
			if (existingIndex >= 0) {
				newPermissions.splice(existingIndex, 1);
			}
		}

		// Update local state and notify parent
		//localSelectedPermissions = newPermissions;
		localSelectedPermissions = [...newPermissions];
		updateTrigger++;
		if (onPermissionsChange) {
			onPermissionsChange([...newPermissions]);
		}
	}

	// ------------------------------
	// SELECTION HANDLERS
	// ------------------------------

	function getModuleSubtreeIds(
		module: ModuleDetail
	): { id: string; allActions: string[]; viewActions: string[] }[] {
		const ids: { id: string; allActions: string[]; viewActions: string[] }[] = [];

		// Module itself
		if (module.allowed_actions?.length) {
			ids.push({
				id: module.id,
				allActions: module.allowed_actions.map((a) => a.action_key),
				viewActions: module.allowed_actions.filter(isViewAction).map((a) => a.action_key)
			});
		}

		// Menus and their cards
		module.menus?.forEach((menu) => {
			if (menu.allowed_actions?.length) {
				ids.push({
					id: menu.id,
					allActions: menu.allowed_actions.map((a) => a.action_key),
					viewActions: menu.allowed_actions.filter(isViewAction).map((a) => a.action_key)
				});
			}
			menu.cards?.forEach((card) => {
				if (card.allowed_actions?.length) {
					ids.push({
						id: card.id,
						allActions: card.allowed_actions.map((a) => a.action_key),
						viewActions: card.allowed_actions.filter(isViewAction).map((a) => a.action_key)
					});
				}
			});
		});

		return ids;
	}

	function getMenuSubtreeIds(
		menu: MenuDetail
	): { id: string; allActions: string[]; viewActions: string[] }[] {
		const ids: { id: string; allActions: string[]; viewActions: string[] }[] = [];

		// Menu itself
		if (menu.allowed_actions?.length) {
			ids.push({
				id: menu.id,
				allActions: menu.allowed_actions.map((a) => a.action_key),
				viewActions: menu.allowed_actions.filter(isViewAction).map((a) => a.action_key)
			});
		}

		// Cards
		menu.cards?.forEach((card) => {
			if (card.allowed_actions?.length) {
				ids.push({
					id: card.id,
					allActions: card.allowed_actions.map((a) => a.action_key),
					viewActions: card.allowed_actions.filter(isViewAction).map((a) => a.action_key)
				});
			}
		});

		return ids;
	}

	function updateMultiplePermissions(updates: { structureId: string; actionKeys: string[] }[]) {
		let newPermissions = [...localSelectedPermissions];

		updates.forEach(({ structureId, actionKeys }) => {
			const existingIndex = newPermissions.findIndex(
				(item) => item.permissstruct_id === structureId
			);
			if (actionKeys.length > 0) {
				if (existingIndex >= 0) {
					newPermissions[existingIndex] = {
						permissstruct_id: structureId,
						granted_action_key: actionKeys
					};
				} else {
					newPermissions.push({ permissstruct_id: structureId, granted_action_key: actionKeys });
				}
			} else {
				if (existingIndex >= 0) {
					newPermissions.splice(existingIndex, 1);
				}
			}
		});

		localSelectedPermissions = newPermissions;
		updateTrigger++;
		if (onPermissionsChange) onPermissionsChange(newPermissions);
	}

	function handleModuleSelection(module: ModuleDetail, event: Event) {
		if (isViewMode) return;
		event.stopPropagation();

		const subtree = getModuleSubtreeIds(module);
		const fullySelected = isModuleFullySelected(module, localSelectedPermissions);
		const partiallySelected = isModulePartiallySelected(module, localSelectedPermissions);

		// Logic B: If any selection exists (Full or Partial), Clear All. Else, Select View Only.
		const hasAnySelection = fullySelected || partiallySelected;

		const updates = subtree.map((item) => ({
			structureId: item.id,
			actionKeys: hasAnySelection ? [] : item.viewActions
		}));

		updateMultiplePermissions(updates);
	}

	function handleMenuSelection(menu: MenuDetail, event: Event) {
		if (isViewMode) return;
		event.stopPropagation();

		const subtree = getMenuSubtreeIds(menu);
		const fullySelected = isMenuFullySelected(menu, localSelectedPermissions);
		const partiallySelected = isMenuPartiallySelected(menu, localSelectedPermissions);

		const hasAnySelection = fullySelected || partiallySelected;

		const updates = subtree.map((item) => ({
			structureId: item.id,
			actionKeys: hasAnySelection ? [] : item.viewActions
		}));

		updateMultiplePermissions(updates);
	}

	function handleCardSelection(card: CardDetail, event: Event) {
		if (isViewMode) return;
		event.stopPropagation();

		// Card is a leaf
		const allActionKeys = getAllActionKeysForStructure(card);
		const currentActions = getGrantedActions(card.id);

		// For leaf nodes: Standard toggle behavior
		// If all selected -> Clear
		// If partial/none -> Select All (Wait, user said "selecting parent should select... only view". Does a card count as a parent of its actions?)
		// "any action selected or unselected at child to propagate back..."
		// If I click the Card checkbox:
		// User might expect "Select View Only" here too?
		// "selecting parent should select the child and the action only view action in the childs" -> Card is a parent of actions? Yes.
		// So if I click Card, maybe I should only select View actions too?
		// Current behavior: Select All Actions.
		// Let's stick to standard Select All for Card unless specified, but user's intent seems to point to "Safe Selection by Default".
		// "selecting parent... only view...". Card contains actions.
		// Let's match the pattern for Cards too: Select View Only if empty. Clear if populated.
		// BUT cards often have only 1-2 actions. If I click card, I usually want access.
		// Let's assume Card -> Select View Only as well for consistency, IF it has view actions.

		const viewActions = card.allowed_actions?.filter(isViewAction).map((a) => a.action_key) || [];

		// Check state
		const allSelected =
			allActionKeys.length > 0 && allActionKeys.every((k) => currentActions.includes(k));
		const isPartial = currentActions.length > 0 && !allSelected;

		const hasAny = currentActions.length > 0;

		// If has any -> Clear.
		// If none -> Select View Only (if available), else Select All?
		// If no view actions exist, we should probably Select All to allow access?
		const targetActions = viewActions.length > 0 ? viewActions : allActionKeys;

		updateStructurePermission(card.id, hasAny ? [] : targetActions);
	}

	function handleActionSelection(structureId: string, actionKey: string, event: Event) {
		if (isViewMode) return;
		event.stopPropagation(); // prevent parent click

		const currentActions = getGrantedActions(structureId);
		let newActions: string[];

		if (currentActions.includes(actionKey)) {
			// Remove
			newActions = currentActions.filter((k) => k !== actionKey);
		} else {
			// Add
			newActions = [...currentActions, actionKey];
		}

		updateStructurePermission(structureId, newActions);
	}

	// ------------------------------
	// SELECTION STATE CHECKERS (Updated for cascading)
	// ------------------------------

	function isModuleFullySelected(module: ModuleDetail, _dep?: any): boolean {
		const subtree = getModuleSubtreeIds(module);
		if (subtree.length === 0) return false;

		// A node is "fully selected" if:
		// 1. It has actions AND all are granted
		// 2. OR it has NO actions (container only) - but we shouldn't rely on this for the root module check if we want visual feedback based on children.
		// Wait, getModuleSubtreeIds returns flat list including the module itself.

		// Logic Fix:
		// If a node has actions, checking them is sufficient.
		// If a node has NO actions (like a category wrapper), it shouldn't fail the check, BUT the module relies on *visible* things being selected.
		// The issue is `node.allActions.every` returns TRUE for empty arrays.

		// Critical addition: If we have NO effectively actionable nodes, then we can't be "selected".
		const actionableNodes = subtree.filter((n) => n.allActions.length > 0);
		if (actionableNodes.length === 0) return false;

		// Re-evaluate result based only on actionable nodes
		const actionableResult = actionableNodes.every((node) => {
			const granted = getGrantedActions(node.id);
			return node.allActions.every((k) => granted.includes(k));
		});

		return actionableResult;
	}

	function isModulePartiallySelected(module: ModuleDetail, _dep?: any): boolean {
		const subtree = getModuleSubtreeIds(module);
		if (subtree.length === 0) return false;

		let totalActions = 0;
		let totalGranted = 0;

		subtree.forEach((node) => {
			totalActions += node.allActions.length;
			const granted = getGrantedActions(node.id);
			totalGranted += granted.filter((k) => node.allActions.includes(k)).length;
		});

		return totalGranted > 0 && totalGranted < totalActions;
	}

	function isMenuFullySelected(menu: MenuDetail, _dep?: any): boolean {
		const subtree = getMenuSubtreeIds(menu);
		if (subtree.length === 0) return false;

		return subtree.every((node) => {
			const granted = getGrantedActions(node.id);
			return node.allActions.length > 0 && node.allActions.every((k) => granted.includes(k));
		});
	}

	function isMenuPartiallySelected(menu: MenuDetail, _dep?: any): boolean {
		const subtree = getMenuSubtreeIds(menu);
		if (subtree.length === 0) return false;

		let totalActions = 0;
		let totalGranted = 0;

		subtree.forEach((node) => {
			totalActions += node.allActions.length;
			const granted = getGrantedActions(node.id);
			totalGranted += granted.filter((k) => node.allActions.includes(k)).length;
		});

		return totalGranted > 0 && totalGranted < totalActions;
	}

	// Cards are leaves, logic stays mostly same but good to keep structure
	function isCardFullySelected(card: CardDetail, _dep?: any): boolean {
		const allActionKeys = getAllActionKeysForStructure(card);
		const currentActions = getGrantedActions(card.id);
		return allActionKeys.length > 0 && allActionKeys.every((key) => currentActions.includes(key));
	}

	function isCardPartiallySelected(card: CardDetail, _dep?: any): boolean {
		const allActionKeys = getAllActionKeysForStructure(card);
		const currentActions = getGrantedActions(card.id);
		if (allActionKeys.length === 0) return false;

		const selectedCount = currentActions.filter((key) => allActionKeys.includes(key)).length;
		return selectedCount > 0 && selectedCount < allActionKeys.length;
	}

	// ------------------------------
	// FILTER FUNCTIONS (keep as is)
	// ------------------------------

	function filterItems<T extends { name: string; description: string }>(
		items: T[],
		term: string
	): T[] {
		if (!term) return items;
		const lowerTerm = term.toLowerCase();
		return items.filter(
			(item) =>
				item.name.toLowerCase().includes(lowerTerm) ||
				item.description.toLowerCase().includes(lowerTerm)
		);
	}

	function moduleHasMatches(module: ModuleDetail, term: string): boolean {
		if (!term) return true;
		const lowerTerm = term.toLowerCase();
		if (
			module.name.toLowerCase().includes(lowerTerm) ||
			module.description.toLowerCase().includes(lowerTerm)
		)
			return true;

		return module.menus?.some((menu) => menuHasMatches(menu, term)) || false;
	}

	function menuHasMatches(menu: MenuDetail, term: string): boolean {
		if (!term) return true;
		const lowerTerm = term.toLowerCase();
		if (
			menu.name.toLowerCase().includes(lowerTerm) ||
			menu.description.toLowerCase().includes(lowerTerm)
		)
			return true;

		return menu.cards?.some((card) => cardHasMatches(card, term)) || false;
	}

	function cardHasMatches(card: CardDetail, term: string): boolean {
		if (!term) return true;
		const lowerTerm = term.toLowerCase();
		if (
			card.name.toLowerCase().includes(lowerTerm) ||
			card.description.toLowerCase().includes(lowerTerm)
		)
			return true;

		return (
			card.allowed_actions?.some(
				(action) =>
					action.display_name.toLowerCase().includes(lowerTerm) ||
					action.action_key.toLowerCase().includes(lowerTerm)
			) || false
		);
	}

	// ------------------------------
	// UI HELPERS
	// ------------------------------

	function toggleNode(id: string) {
		const newExpanded = new Set(expandedNodes);
		if (newExpanded.has(id)) {
			newExpanded.delete(id);
		} else {
			newExpanded.add(id);
		}
		expandedNodes = newExpanded;
	}

	function expandAllNodes() {
		if (!permissionData) return;
		const newExpanded = new Set<string>();

		permissionData.modules.forEach((module) => {
			newExpanded.add(module.id);
			module.menus?.forEach((menu) => {
				newExpanded.add(menu.id);
				menu.cards?.forEach((card) => newExpanded.add(card.id));
			});
		});

		expandedNodes = newExpanded;
	}

	function collapseAllNodes() {
		expandedNodes = new Set();
	}

	function selectAllPermissions() {
		if (isViewMode || !permissionData) return;

		const newPermissions: Array<{ permissstruct_id: string; granted_action_key: string[] }> = [];

		permissionData.modules.forEach((module) => {
			if (module.allowed_actions?.length) {
				newPermissions.push({
					permissstruct_id: module.id,
					granted_action_key: module.allowed_actions.map((a) => a.action_key)
				});
			}

			module.menus?.forEach((menu) => {
				if (menu.allowed_actions?.length) {
					newPermissions.push({
						permissstruct_id: menu.id,
						granted_action_key: menu.allowed_actions.map((a) => a.action_key)
					});
				}

				menu.cards?.forEach((card) => {
					if (card.allowed_actions?.length) {
						newPermissions.push({
							permissstruct_id: card.id,
							granted_action_key: card.allowed_actions.map((a) => a.action_key)
						});
					}
				});
			});
		});

		//localSelectedPermissions = newPermissions;
		localSelectedPermissions = [...newPermissions];
		updateTrigger++;
		if (onPermissionsChange) {
			onPermissionsChange(newPermissions);
		}
	}

	function clearAllPermissions() {
		if (isViewMode) return;
		localSelectedPermissions = [];
		updateTrigger++;
		if (onPermissionsChange) {
			onPermissionsChange([]);
		}
	}

	// Auto-expand search results
	$: if (searchTerm && permissionData) {
		const nodesToExpand = new Set<string>();
		permissionData.modules.forEach((module) => {
			if (moduleHasMatches(module, searchTerm)) {
				nodesToExpand.add(module.id);
				module.menus?.forEach((menu) => {
					if (menuHasMatches(menu, searchTerm)) {
						nodesToExpand.add(menu.id);
						menu.cards?.forEach((card) => {
							if (cardHasMatches(card, searchTerm)) nodesToExpand.add(card.id);
						});
					}
				});
			}
		});
		expandedNodes = nodesToExpand;
	}

	// Get permission type badge
	function getPermissionType(structureId: string): string {
		if (!permissionData) return '';

		// Check if it's a module
		if (permissionData.modules.some((m) => m.id === structureId)) return 'Module';

		// Check if it's a menu
		for (const module of permissionData.modules) {
			if (module.menus?.some((m) => m.id === structureId)) return 'Menu';
		}

		// Otherwise it's a card
		return 'Card';
	}

	function getPermissionTypeColor(type: string): string {
		switch (type) {
			case 'Module':
				return 'bg-purple-100 text-purple-800 border-purple-200';
			case 'Menu':
				return 'bg-blue-100 text-blue-800 border-blue-200';
			case 'Card':
				return 'bg-green-100 text-green-800 border-green-200';
			default:
				return 'bg-gray-100 text-gray-800 border-gray-200';
		}
	}
</script>

<div class="permission-tree bg-white rounded-lg shadow-sm {isViewMode ? 'opacity-95' : ''}">
	<!-- Search & Actions -->
	<div class="search-section bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4">
		<input
			type="text"
			bind:value={searchTerm}
			placeholder="Search modules, menus, cards, or permissions..."
			class="search-input w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent mb-3"
		/>
		<div class="search-actions flex flex-wrap gap-2">
			<button
				on:click={expandAllNodes}
				class="btn bg-white border border-gray-300 rounded px-3 py-1 text-sm hover:bg-gray-50 transition-colors"
				>Expand All</button
			>
			<button
				on:click={collapseAllNodes}
				class="btn bg-white border border-gray-300 rounded px-3 py-1 text-sm hover:bg-gray-50 transition-colors"
				>Collapse All</button
			>
			{#if !isViewMode}
				<button
					on:click={selectAllPermissions}
					class="btn bg-white border border-gray-300 rounded px-3 py-1 text-sm hover:bg-gray-50 transition-colors"
					>Select All</button
				>
				<button
					on:click={clearAllPermissions}
					class="btn bg-white border border-gray-300 rounded px-3 py-1 text-sm hover:bg-gray-50 transition-colors"
					>Clear All</button
				>
			{/if}
		</div>
	</div>

	<!-- Tree -->
	<div class="tree-container border border-gray-200 rounded-lg bg-white p-4">
		{#if loading}
			<div class="loading-message text-gray-500 text-center py-5 italic">
				Loading permission structure...
			</div>
		{:else if permissionData}
			<!-- View Mode Banner -->
			{#if isViewMode}
				<div
					class="view-mode-banner bg-blue-50 border border-blue-200 rounded-md p-3 mb-4 text-center"
				>
					<p class="text-blue-700 font-medium text-sm">👁️ View Mode - Permissions are read-only</p>
				</div>
			{/if}

			<!-- Summary -->
			<div class="summary-stats mb-4 p-3 bg-gray-50 rounded-lg">
				<div class="flex justify-between items-center">
					<div>
						<span class="text-sm text-gray-600"
							>Selected: <strong
								>{localSelectedPermissions.reduce(
									(total, perm) => total + perm.granted_action_key.length,
									0
								)}</strong
							>
							actions across <strong>{localSelectedPermissions.length}</strong> structures</span
						>
						<div class="text-xs text-gray-500 mt-1">
							Modules: {permissionData.modules?.length || 0} | Menus: {permissionData.modules?.reduce(
								(total, m) => total + (m.menus?.length || 0),
								0
							)} | Cards: {permissionData.modules?.reduce(
								(total, m) =>
									total +
									m.menus?.reduce((menuTotal, menu) => menuTotal + (menu.cards?.length || 0), 0),
								0
							)}
						</div>
					</div>
					{#if !isViewMode}
						<button on:click={clearAllPermissions} class="text-sm text-red-600 hover:text-red-800"
							>Clear Selection</button
						>
					{/if}
				</div>
			</div>

			<!-- Modules Grid -->
			<div class="modules-grid grid grid-cols-1 xl:grid-cols-2 gap-6 lg:gap-8 items-start">
				{#each permissionData.modules as module (module.id)}
					{#if moduleHasMatches(module, searchTerm)}
						<!-- MODULE -->
						<div class="module-wrapper relative">
							<div
								class="count-badge absolute -top-2 -left-2 bg-purple-600 text-white rounded-full px-2 py-1 text-xs font-bold shadow-lg border-2 border-white z-10"
							>
								{module.allowed_actions?.length || 0} actions
							</div>
							<div
								class="module-container bg-purple-50 border-2 border-purple-500 rounded-lg shadow-sm {isViewMode
									? ''
									: 'hover:shadow-md transition-all duration-300 hover:-translate-y-1'} h-fit ml-2 mt-2"
							>
								<!-- Module Header -->
								<div
									role="button"
									tabindex="0"
									class="node-header module-header bg-purple-600 text-white px-4 py-3 rounded-t-lg cursor-pointer select-none {isViewMode
										? 'hover:bg-purple-600'
										: 'hover:bg-purple-700'} transition-colors flex items-center gap-3"
									on:click={() => toggleNode(module.id)}
									on:keydown={(e) => {
										if (e.key === 'Enter' || e.key === ' ') {
											e.preventDefault();
											toggleNode(module.id);
										}
									}}
								>
									<input
										type="checkbox"
										class="h-4 w-4 {isViewMode ? 'cursor-default opacity-70' : 'cursor-pointer'}"
										checked={isModuleFullySelected(module, localSelectedPermissions)}
										indeterminate={isModulePartiallySelected(module, localSelectedPermissions) &&
											!isModuleFullySelected(module, localSelectedPermissions)}
										on:click={(e) => handleModuleSelection(module, e)}
										on:change={() => {}}
										disabled={isViewMode}
									/>
									<span class="icon text-lg">{module.icon || '📦'}</span>
									<span class="name font-semibold text-sm">{module.name}</span>
									<span class="description text-purple-100 text-sm flex-1">
										- {module.description}</span
									>
									<span class="expand-icon text-xs opacity-90"
										>{expandedNodes.has(module.id) ? '▼' : '▶'}</span
									>
								</div>

								{#if expandedNodes.has(module.id)}
									<div class="module-children p-4 bg-white/50 rounded-b-lg space-y-3">
										<!-- Module-level actions -->
										{#if module.allowed_actions && module.allowed_actions.length > 0}
											<div class="module-actions-section mb-4">
												<h4 class="text-sm font-semibold text-purple-700 mb-2">Module Actions</h4>
												<div class="space-y-2 pl-4">
													{#each module.allowed_actions as action (action.action_key)}
														<div class="action-item flex items-center gap-2">
															<input
																type="checkbox"
																class="h-4 w-4 {isViewMode
																	? 'cursor-default opacity-70'
																	: 'cursor-pointer'}"
																checked={isActionGranted(
																	module.id,
																	action.action_key,
																	localSelectedPermissions
																)}
																on:click={(e) =>
																	handleActionSelection(module.id, action.action_key, e)}
																on:change={() => {}}
																disabled={isViewMode}
															/>
															<span class="name text-sm">{action.display_name}</span>
															<span
																class="text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-800 border border-purple-200"
																>Module</span
															>
															<span class="description text-gray-500 text-xs flex-1">
																- {module.name}: {action.display_name}</span
															>
														</div>
													{/each}
												</div>
											</div>
										{/if}

										<!-- Menus -->
										{#each module.menus as menu (menu.id)}
											{#if menuHasMatches(menu, searchTerm)}
												<!-- MENU -->
												<div
													class="menu-container bg-blue-50 border-2 border-blue-500 rounded-lg shadow-sm {isViewMode
														? ''
														: 'transition-all duration-200'}"
												>
													<button
														type="button"
														class="node-header menu-header bg-blue-600 text-white px-4 py-3 rounded-t-lg cursor-pointer select-none {isViewMode
															? 'hover:bg-blue-600'
															: 'hover:bg-blue-700'} transition-colors flex items-center gap-3 w-full text-left"
														on:click={() => toggleNode(menu.id)}
														aria-expanded={expandedNodes.has(menu.id)}
													>
														<input
															type="checkbox"
															class="h-4 w-4 {isViewMode
																? 'cursor-default opacity-70'
																: 'cursor-pointer'}"
															checked={isMenuFullySelected(menu, localSelectedPermissions)}
															indeterminate={isMenuPartiallySelected(
																menu,
																localSelectedPermissions
															) && !isMenuFullySelected(menu, localSelectedPermissions)}
															on:click={(e) => handleMenuSelection(menu, e)}
															on:change={() => {}}
															disabled={isViewMode}
														/>
														<span class="icon text-lg">📋</span>
														<span class="name font-semibold text-sm">{menu.name}</span>
														<span class="description text-blue-100 text-sm flex-1 min-w-0">
															- {menu.description}</span
														>
														<span class="expand-icon text-xs opacity-90"
															>{expandedNodes.has(menu.id) ? '▼' : '▶'}</span
														>
													</button>

													{#if expandedNodes.has(menu.id)}
														<div class="menu-children p-3 bg-white/60 rounded-b-lg space-y-2">
															<!-- Menu-level actions -->
															{#if menu.allowed_actions && menu.allowed_actions.length > 0}
																<div class="menu-actions-section mb-3">
																	<h5 class="text-xs font-semibold text-blue-700 mb-1">
																		Menu Actions
																	</h5>
																	<div class="space-y-1 pl-4">
																		{#each menu.allowed_actions as action (action.action_key)}
																			<div class="action-item flex items-center gap-2">
																				<input
																					type="checkbox"
																					class="h-3 w-3 {isViewMode
																						? 'cursor-default opacity-70'
																						: 'cursor-pointer'}"
																					checked={isActionGranted(
																						menu.id,
																						action.action_key,
																						localSelectedPermissions
																					)}
																					on:click={(e) =>
																						handleActionSelection(menu.id, action.action_key, e)}
																					on:change={() => {}}
																					disabled={isViewMode}
																				/>
																				<span class="name text-xs">{action.display_name}</span>
																				<span
																					class="text-xs px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-800 border border-blue-200"
																					>Menu</span
																				>
																			</div>
																		{/each}
																	</div>
																</div>
															{/if}

															<!-- Cards -->
															{#each menu.cards as card (card.id)}
																{#if cardHasMatches(card, searchTerm)}
																	<!-- CARD -->
																	<div
																		class="card-container bg-green-50 border-2 border-green-500 rounded-lg shadow-sm {isViewMode
																			? ''
																			: 'transition-all duration-200'}"
																	>
																		<button
																			type="button"
																			class="node-header card-header bg-green-500 text-gray-900 px-4 py-2 rounded-t-lg cursor-pointer select-none {isViewMode
																				? 'hover:bg-green-500'
																				: 'hover:bg-green-600'} transition-colors flex items-center gap-3 w-full text-left"
																			on:click={() => toggleNode(card.id)}
																			aria-expanded={expandedNodes.has(card.id)}
																		>
																			<input
																				type="checkbox"
																				class="h-4 w-4 {isViewMode
																					? 'cursor-default opacity-70'
																					: 'cursor-pointer'}"
																				checked={isCardFullySelected(
																					card,
																					localSelectedPermissions
																				)}
																				indeterminate={isCardPartiallySelected(
																					card,
																					localSelectedPermissions
																				) && !isCardFullySelected(card, localSelectedPermissions)}
																				on:click={(e) => handleCardSelection(card, e)}
																				on:change={() => {}}
																				disabled={isViewMode}
																			/>
																			<span class="icon text-lg">📄</span>
																			<span class="name font-semibold text-sm">{card.name}</span>
																			<span
																				class="description text-gray-700 text-sm flex-1 min-w-0"
																			>
																				- {card.description}</span
																			>
																			<span class="expand-icon text-xs opacity-90"
																				>{expandedNodes.has(card.id) ? '▼' : '▶'}</span
																			>
																		</button>

																		{#if expandedNodes.has(card.id)}
																			<div
																				class="card-children p-3 bg-white rounded-b-lg space-y-1"
																			>
																				<!-- Card-level actions -->
																				{#if card.allowed_actions && card.allowed_actions.length > 0}
																					<div class="card-actions-section mb-2">
																						<h6 class="text-xs font-semibold text-green-700 mb-1">
																							Card Actions
																						</h6>
																						<div class="space-y-1 pl-4">
																							{#each card.allowed_actions as action (action.action_key)}
																								<div class="action-item flex items-center gap-2">
																									<input
																										type="checkbox"
																										class="h-3 w-3 {isViewMode
																											? 'cursor-default opacity-70'
																											: 'cursor-pointer'}"
																										checked={isActionGranted(
																											card.id,
																											action.action_key,
																											localSelectedPermissions
																										)}
																										on:click={(e) =>
																											handleActionSelection(
																												card.id,
																												action.action_key,
																												e
																											)}
																										on:change={() => {}}
																										disabled={isViewMode}
																									/>
																									<span class="name text-xs"
																										>{action.display_name}</span
																									>
																									<span
																										class="text-xs px-1.5 py-0.5 rounded-full bg-green-100 text-green-800 border border-green-200"
																										>Card</span
																									>
																								</div>
																							{/each}
																						</div>
																					</div>
																				{/if}
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
			<div class="text-gray-500 text-center py-5 italic">No permission structure available</div>
		{/if}
	</div>
</div>

<style>
	.permission-tree {
		max-width: 100%;
	}

	input[indeterminate] {
		accent-color: gray;
	}
</style>
