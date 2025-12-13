<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { permissionStructureStore } from '$lib/permission/stores/permission_readonly_stores';
	import { rolesStore, usersStore } from '$lib/permission/stores/permission_entity_stores';
	import { PermissionUtils } from '$lib/permission/utils_permission';
	import PermissionTree from './PermissionTree.svelte';
	import { useMutations, useLookup } from '$lib/common/controls';
	import type {
		Role,
		PermissionStructure,
		RolePermissions
	} from '$lib/permission/stores/types_permission';

	// Props for different modes
	export let mode = 'view'; // 'new' | 'view' | 'edit'
	export let roleId;
	export let onSave: (() => void) | null = null;
	export let onCancel: (() => void) | null = null;

	// Local state
	let roleData = {
		display_name: '',
		description: '',
		power_level: 0,
		users: 0,
		permissions: [] as RolePermissions[]
	};

	let originalRoleData: typeof roleData | null = null;
	let saveLoading = false;
	let saveMessage = '';
	let initialized = false;
	let permissionerror = false;

	// Use control helpers
	const { addItem: addRoleMutation, updateItem: updateRoleMutation } = useMutations(rolesStore);
	const { getEntities: getRoleById } = useLookup(rolesStore);

	// Destructure to get the actual stores
	const { data: permissionStructureData, loading: permissionStructureLoading } =
		permissionStructureStore;

	// Reactive initialization to handle async loading and prop changes
	$: readyToLoad = $permissionStructureData && !$permissionStructureLoading;

	let currentLoadedId: string | object | null = null;

	$: if (readyToLoad) {
		if (mode === 'new' && !initialized) {
			console.log('RoleEditPage: Initializing New Role');
			roleData = {
				display_name: '',
				description: '',
				power_level: 0,
				users: 0,
				permissions: []
			};
			initialized = true;
		} else if (roleId && (roleId !== currentLoadedId || !initialized)) {
			console.log('RoleEditPage: Loading role data', roleId);
			currentLoadedId = roleId;
			loadRoleData();
		}
	}

	// Power Distribution Calculation for Charts
	$: dist = (() => {
		if (!roleData.permissions.length || !$permissionStructureData) {
			return { low: 0, medium: 0, high: 0, critical: 0 };
		}

		// Handle legacy strings vs new RolePermissions
		let ids: string[] = [];
		const first = roleData.permissions[0];

		if (typeof first === 'string') {
			ids = roleData.permissions as unknown as string[];
		} else {
			// Best-effort mapping for visual chart
			// This maps { permissstruct_id, action_key } -> Permission ID
			ids = (roleData.permissions as RolePermissions[]).flatMap((rp) => {
				const struct = PermissionUtils.findStructureById(
					rp.permissstruct_id,
					$permissionStructureData!
				);
				if (!struct) return [];

				let perms: any[] = [];
				// Check if structure has direct permissions list (Menus, Cards)
				if ('permissions' in struct && Array.isArray((struct as any).permissions)) {
					perms = (struct as any).permissions;
				}

				return rp.granted_action_key
					.map((action) => {
						const p = perms.find((p) => p.permission_action === action);
						return p ? p.id : null;
					})
					.filter((id): id is string => id !== null);
			});
		}

		return PermissionUtils.getPowerDistribution(ids, $permissionStructureData);
	})();

	onMount(async () => {
		if (!$permissionStructureData && !$permissionStructureLoading) {
			await permissionStructureStore.load();
		}
	});

	/* REMOVED initializeRoleData as it's replaced by reactive logic */

	async function loadRoleData() {
		let role;
		try {
			// Ensure roleId is a string
			let lookupId = roleId;
			if (typeof roleId === 'object' && roleId !== null) {
				lookupId = (roleId as any).role_id || (roleId as any).id;
			}

			if (!lookupId || typeof lookupId !== 'string') {
				console.error('Invalid roleId:', roleId);
				saveMessage = '❌ Invalid role ID';
				return;
			}

			// Always fetch the role by ID
			if (getRoleById) {
				role = await getRoleById(lookupId);

				// Fallback: Case-insensitive search if not found
				if (!role) {
					console.log(`Role ${lookupId} not found directly, trying case-insensitive search...`);
					// If rolesStore doesn't expose getAll directly in this context, we might rely on what's available
					// But standard useLookup usually provides getEntities.

					// Since we can't easily access all roles if getRoleById is just a lookup, we'll try to rely on what we have.
					// However, if getRoleById returns null, we can't do much without access to the list.
					// Let's assume getRoleById works for now, or try lowercase.

					if (/[A-Z]/.test(lookupId)) {
						const lowerId = lookupId.toLowerCase();
						role = await getRoleById(lowerId);
					}
				}
			}

			if (!role) {
				// Try to look into the raw store if useLookup failed or if we need to iterate
				// Accessing the store value directly since we imported it
				const $roles = $rolesStore;
				if ($roles && Array.isArray($roles)) {
					role = $roles.find(
						(r) => r.role_id === lookupId || r.role_id === lookupId?.toLowerCase()
					);
				}
			}

			if (!role) {
				saveMessage = '❌ Role not found';
				return;
			}

			const typedRole = role as Role;

			// 1. Initial Data Population (Set power_level to 0 initially if permissions might be wrong format)
			roleData = {
				display_name: typedRole.display_name,
				description: typedRole.description,
				power_level: typedRole.power_level || 0, // Recalculate later for safety
				users: typedRole.user_count || 0,
				permissions: []
			};

			// 2. Check for legacy/backend formats & Normalize
			let legacyIds: string[] = [];
			let rawPermissions: any[] = [];

			// Backend might send 'permission_ids' (strings or objects) or 'permissions'
			if (typedRole.permission_ids && typedRole.permission_ids.length > 0) {
				rawPermissions = typedRole.permission_ids;
			} else if (typedRole.permissions && typedRole.permissions.length > 0) {
				rawPermissions = typedRole.permissions;
			}

			if (rawPermissions.length > 0) {
				const first = rawPermissions[0];

				// Handle string IDs
				if (typeof first === 'string') {
					console.log('RoleEditPage: Detected string permission IDs');
					legacyIds = rawPermissions as string[];
				}
				// Handle Objects
				else if (typeof first === 'object') {
					if ('permissstruct_id' in first) {
						// New Structured Format
						// CRITICAL FIX: Cast permissstruct_id to String to match Structure IDs
						console.log('RoleEditPage: Detected structured permissions - Normalizing IDs');
						roleData.permissions = rawPermissions.map((p: any) => ({
							permissstruct_id: String(p.permissstruct_id),
							granted_action_key: p.granted_action_key
						}));
					} else if ('permission_id' in first) {
						// Legacy Backend Format
						console.log('RoleEditPage: Detected legacy permission objects');
						legacyIds = rawPermissions.map((p: any) => p.permission_id);
					}
				}
			}

			// 3. Convert legacy IDs if found
			if (legacyIds.length > 0) {
				console.log('RoleEditPage: Converting legacy IDs...', legacyIds.length);
				const struct = $permissionStructureData;
				if (struct) {
					const converted: RolePermissions[] = [];
					const map = new Map<string, Set<string>>();

					legacyIds.forEach((pid) => {
						const detail = PermissionUtils.findPermissionById(pid, struct);
						if (detail) {
							// Need to find parent structure ID
							let parentId: string | undefined;

							// Search modules for the parent of this permission ID
							// Note: detail.id === pid
							for (const m of struct.modules) {
								if (m.menus) {
									for (const menu of m.menus) {
										if (menu.permissions && menu.permissions.some((p) => p.id === pid)) {
											parentId = menu.id;
											break;
										}
										if (menu.cards) {
											for (const card of menu.cards) {
												if (card.permissions && card.permissions.some((p) => p.id === pid)) {
													parentId = card.id;
													break;
												}
											}
										}
										if (parentId) break;
									}
								}
								if (parentId) break;
							}

							if (parentId) {
								if (!map.has(parentId)) map.set(parentId, new Set());
								// Use permission_action as the key (e.g. 'view', 'edit')
								// This maps to granted_action_key in new structure
								map.get(parentId)?.add(detail.permission_action);
							}
						}
					});

					map.forEach((actions, structId) => {
						converted.push({
							permissstruct_id: structId,
							granted_action_key: Array.from(actions)
						});
					});

					roleData.permissions = converted;
					console.log('RoleEditPage: Converted result:', roleData.permissions);
				}
			}

			// Store original data for cancel/discard (deep copy)
			originalRoleData = JSON.parse(JSON.stringify(roleData));
			initialized = true;
		} catch (err) {
			console.error('Failed to load role data:', err);
			saveMessage = '❌ Failed to load role data';
		}
	}

	async function saveRole() {
		if (mode === 'view') return;

		saveLoading = true;
		saveMessage = '';

		// Validation for new role
		if (mode === 'new' && !roleData.display_name.trim()) {
			saveMessage = '❌ Role name is required';
			saveLoading = false;
			return;
		}

		try {
			let result;

			if (mode === 'new') {
				// Create new role
				if (!addRoleMutation) throw new Error('Role creation not available');

				const newRoleData: Partial<Role> = {
					role_id: roleData.display_name.toLowerCase().replace(/\s+/g, '_'),
					display_name: roleData.display_name,
					description: roleData.description,
					permissions: roleData.permissions,
					power_level: roleData.power_level,
					permission_count: roleData.permissions.length,
					category_access: [],
					is_system_role: false
				};

				result = await addRoleMutation(newRoleData);
				saveMessage = '✅ Role created successfully!';
			} else {
				// Update existing role
				if (!updateRoleMutation) throw new Error('Role update not available');

				// Compute only changed fields
				const changedFields = diffData(originalRoleData, roleData);
				changedFields.role_id = roleId!;
				if (Object.keys(changedFields).length === 0) {
					saveMessage = 'ℹ️ No changes to save';
					return;
				}

				if (changedFields.permissions) {
					changedFields.permission_count = changedFields.permissions.length;
				}

				const updateData: Partial<Role>[] = [changedFields];
				result = await updateRoleMutation([roleId!], updateData);
				saveMessage = '✅ Role updated successfully!';
			}

			// Call parent callback or fallback navigation
			if (onSave) {
				setTimeout(() => onSave(), 500);
			} else {
				setTimeout(() => goto('/permission/roles'), 1500);
			}
		} catch (error) {
			console.error('Error saving role:', error);
			saveMessage = '❌ Failed to save role';
		} finally {
			saveLoading = false;
		}
	}

	function cancelEdit() {
		if (onCancel) {
			// Use parent callback if provided
			onCancel();
		} else if (mode === 'new') {
			// Fallback to navigation only if no callback
			goto('/permission/roles');
		} else if (originalRoleData) {
			// For edit mode without callback, restore data
			roleData = { ...originalRoleData };
			if (mode === 'edit') {
				mode = 'view';
			}
		}
	}

	function editRole() {
		mode = 'edit';
	}

	function getHeaderTitle() {
		switch (mode) {
			case 'new':
				return 'Create New Role';
			case 'view':
				return `View Role: ${roleData.display_name}`;
			case 'edit':
				return `Edit Role: ${roleData.display_name}`;
			default:
				return 'Role Management';
		}
	}

	// Utility to compute changes between original and current role data
	function diffData(original: any, current: any) {
		const changed: any = {};
		for (const key in current) {
			if (JSON.stringify(current[key]) !== JSON.stringify(original[key])) {
				changed[key] = current[key];
			}
		}
		return changed;
	}

	function getPowerLevelColor(level: number) {
		if (level <= 30) return 'from-emerald-500 to-green-400';
		if (level <= 60) return 'from-amber-500 to-yellow-400';
		if (level <= 80) return 'from-orange-500 to-amber-400';
		return 'from-rose-500 to-red-400';
	}

	function getPowerLevelBg(level: number) {
		if (level <= 30) return 'bg-gradient-to-r from-emerald-100 to-green-100 text-emerald-800';
		if (level <= 60) return 'bg-gradient-to-r from-amber-100 to-yellow-100 text-amber-800';
		if (level <= 80) return 'bg-gradient-to-r from-orange-100 to-amber-100 text-orange-800';
		return 'bg-gradient-to-r from-rose-100 to-red-100 text-rose-800';
	}

	function getActionButtonText() {
		switch (mode) {
			case 'new':
				return 'Create Role';
			case 'edit':
				return 'Save Changes';
			default:
				return 'Save';
		}
	}

	// Mock getPowerDistribution
	function getPowerDistribution(roleKey: string) {
		return {
			low: Math.floor(Math.random() * 10),
			medium: Math.floor(Math.random() * 10),
			high: Math.floor(Math.random() * 10),
			critical: Math.floor(Math.random() * 10)
		};
	}

	// Example: create a mock distribution for a role
	let distribution: { low: number; medium: number; high: number; critical: number } =
		getPowerDistribution('mockRoleKey');

	// Update power level when permissions change
	$: if ($permissionStructureData && roleData.permissions.length > 0) {
		roleData.power_level = PermissionUtils.getMaxPower(
			roleData.permissions,
			$permissionStructureData
		);
	}

	// Deep comparison for permissions (order independent)
	function arePermissionsEqual(
		permsA: { permissstruct_id: string; granted_action_key: string[] }[],
		permsB: { permissstruct_id: string; granted_action_key: string[] }[]
	): boolean {
		if (permsA.length !== permsB.length) return false;

		// Sort by ID
		const sortedA = [...permsA].sort((a, b) =>
			a.permissstruct_id.localeCompare(b.permissstruct_id)
		);
		const sortedB = [...permsB].sort((a, b) =>
			a.permissstruct_id.localeCompare(b.permissstruct_id)
		);

		for (let i = 0; i < sortedA.length; i++) {
			const itemA = sortedA[i];
			const itemB = sortedB[i];

			if (itemA.permissstruct_id !== itemB.permissstruct_id) return false;

			// Compare actions (sorted)
			const actionsA = [...itemA.granted_action_key].sort();
			const actionsB = [...itemB.granted_action_key].sort();

			if (JSON.stringify(actionsA) !== JSON.stringify(actionsB)) return false;
		}
		return true;
	}

	$: hasChanges = originalRoleData
		? roleData.display_name !== originalRoleData.display_name ||
			roleData.description !== originalRoleData.description ||
			!arePermissionsEqual(roleData.permissions, originalRoleData.permissions)
		: false;
</script>

<svelte:head>
	<title>{getHeaderTitle()} - Role Management</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 py-8">
	<div class="w-full px-4 sm:px-6 lg:px-8">
		<!-- Loading State -->
		{#if $permissionStructureLoading || !initialized}
			<div class="flex justify-center items-center py-12">
				<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
				<span class="ml-4 text-gray-600">
					{#if mode === 'new'}
						Initializing new role...
					{:else}
						Loading role data...
					{/if}
				</span>
			</div>
		{:else if permissionerror}
			<div class="premium-card p-6 text-center">
				<div class="text-yellow-800">
					<p class="font-medium">Unable to load permission structure</p>
					<p class="text-sm mt-2">{permissionerror}</p>
					<button
						on:click={() => permissionStructureStore.load()}
						class="mt-4 px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors"
					>
						Retry
					</button>
				</div>
			</div>
		{:else if !$permissionStructureData}
			<div class="premium-card p-6 text-center">
				<div class="text-yellow-800">
					<p class="font-medium">Unable to load permission structure</p>
					<p class="text-sm mt-2">Please check your connection and try again.</p>
					<button
						on:click={() => permissionStructureStore.load()}
						class="mt-4 px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors"
					>
						Retry
					</button>
				</div>
			</div>
		{:else}
			<!-- Role Details and Summary Side by Side - FULL WIDTH -->
			<div class="grid grid-cols-1 xl:grid-cols-4 gap-8 mb-8">
				<!-- Role Details Card - Takes 3/4 width -->
				<div class="xl:col-span-3">
					<div class="premium-card h-full">
						<div class="premium-card-header">
							<h2 class="text-xl font-semibold text-gray-900">
								Role Details
								{#if mode === 'view'}
									<span
										class="ml-2 inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800"
									>
										View Only
									</span>
								{/if}
							</h2>
						</div>
						<div class="p-6 space-y-4">
							<!-- Role Name -->
							<div>
								<label for="role-name" class="block text-sm font-medium text-gray-700 mb-2">
									Role Name {#if mode === 'new'}<span class="text-red-500">*</span>{/if}
								</label>
								<input
									id="role-name"
									type="text"
									bind:value={roleData.display_name}
									placeholder="Enter role name"
									class="premium-input {mode === 'view' ? 'bg-gray-100 cursor-not-allowed' : ''}"
									disabled={mode === 'view'}
								/>
							</div>

							<!-- Role Description -->
							<div>
								<label for="role-description" class="block text-sm font-medium text-gray-700 mb-2">
									Description
								</label>
								<textarea
									id="role-description"
									bind:value={roleData.description}
									placeholder="Enter role description"
									rows="3"
									class="premium-input {mode === 'view' ? 'bg-gray-100 cursor-not-allowed' : ''}"
									disabled={mode === 'view'}
								></textarea>
							</div>

							<!-- Power Level Display -->
							{#if roleData.power_level > 0}
								<div class="mt-4">
									<label class="block text-sm font-medium text-gray-700 mb-2"> Power Level </label>
									<div class="flex items-center space-x-4">
										<div class="relative">
											<div
												class="w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg"
											>
												<span class="text-white font-bold text-lg"
													>{PermissionUtils.getPowerLevelIcon(roleData.power_level)}</span
												>
											</div>
											<div
												class="absolute -bottom-1 -right-1 w-6 h-6 bg-white rounded-full border-2 border-white shadow-lg flex items-center justify-center"
											>
												<div
													class="w-3 h-3 bg-gradient-to-r {getPowerLevelColor(
														roleData.power_level
													)} rounded-full"
												></div>
											</div>
										</div>
										<div>
											<div class="font-semibold text-gray-900 text-lg">
												{roleData.power_level}/100
											</div>
											<div class="text-sm text-gray-500 capitalize">
												{PermissionUtils.getPowerLevelLabel(roleData.power_level)}
											</div>
										</div>
									</div>
								</div>
							{/if}
						</div>
					</div>
				</div>

				<!-- Summary Card - Takes 1/4 width -->
				<div class="xl:col-span-1">
					<div class="premium-card h-full">
						<div class="premium-card-header">
							<h2 class="text-xl font-semibold text-gray-900">Summary</h2>
						</div>
						<div class="p-6 space-y-4">
							<!-- Selected Permissions Count -->
							<div class="text-center">
								<div class="text-3xl font-bold text-gray-900">{roleData.permissions.length}</div>
								<div class="text-sm text-gray-500">Selected Permissions</div>
							</div>

							<!-- Power Level Distribution -->
							{#if roleData.permissions.length > 0 && $permissionStructureData}
								<div class="space-y-3">
									<div class="text-sm font-medium text-gray-700">Power Distribution</div>
									<div class="space-y-2">
										<div class="flex items-center justify-between text-sm">
											<div class="flex items-center space-x-2">
												<div class="w-3 h-3 bg-emerald-500 rounded-full"></div>
												<span class="text-gray-600">Low</span>
											</div>
											<span class="font-semibold text-gray-900">{dist.low}</span>
										</div>
										<div class="flex items-center justify-between text-sm">
											<div class="flex items-center space-x-2">
												<div class="w-3 h-3 bg-amber-500 rounded-full"></div>
												<span class="text-gray-600">Medium</span>
											</div>
											<span class="font-semibold text-gray-900">{dist.medium}</span>
										</div>
										<div class="flex items-center justify-between text-sm">
											<div class="flex items-center space-x-2">
												<div class="w-3 h-3 bg-orange-500 rounded-full"></div>
												<span class="text-gray-600">High</span>
											</div>
											<span class="font-semibold text-gray-900">{dist.high}</span>
										</div>
										<div class="flex items-center justify-between text-sm">
											<div class="flex items-center space-x-2">
												<div class="w-3 h-3 bg-rose-500 rounded-full"></div>
												<span class="text-gray-600">Critical</span>
											</div>
											<span class="font-semibold text-gray-900">{dist.critical}</span>
										</div>
									</div>
								</div>
							{:else}
								<div class="text-center text-sm text-gray-500 py-4">No permissions selected</div>
							{/if}
						</div>
					</div>
				</div>
			</div>

			<!-- Full Width Permission Tree Card -->
			<div class="premium-card mb-8">
				<div class="premium-card-header">
					<h2 class="text-xl font-semibold text-gray-900">
						Permission Assignment
						{#if mode === 'view'}
							<span class="ml-2 text-sm font-normal text-gray-500"
								>(View Only - Expand/Collapse Enabled)</span
							>
						{/if}
					</h2>
				</div>
				<div class="p-6">
					<PermissionTree
						isViewMode={mode === 'view'}
						selectedPermissions={roleData.permissions}
						originalPermissions={originalRoleData?.permissions || []}
						onPermissionsChange={(permissions) => {
							roleData.permissions = permissions;
							// Recalculate power level when permissions change
							if ($permissionStructureData) {
								roleData.power_level = PermissionUtils.getMaxPower(
									permissions,
									$permissionStructureData
								);
							}
						}}
					/>

					<!--
              roleData.permissions = permissions;
              if ($permissionStructureData) {
                roleData.power_level = PermissionUtils.getMaxPower(permissions, $permissionStructureData);
              }
            }}
          /-->
				</div>
			</div>

			<!-- Actions Card -->

			<div class="premium-card">
				<div class="p-6 space-y-4">
					{#if saveMessage}
						<div class="premium-message {saveMessage.includes('✅') ? 'success' : 'error'}">
							<span class="text-lg">{saveMessage.includes('✅') ? '✅' : '❌'}</span>
							<span class="font-medium">{saveMessage}</span>
						</div>
					{/if}

					<!-- Right-aligned button container -->
					<div class="flex justify-end gap-3">
						{#if mode === 'view'}
							<button on:click={editRole} class="premium-primary-btn text-sm px-4 py-2">
								<span class="text-lg">✏️</span>
								<span>Edit Role</span>
							</button>
							<!-- Use onCancel callback for back button -->
							<button
								on:click={onCancel ? onCancel : () => goto('/permission/roles')}
								class="premium-secondary-btn text-sm px-4 py-2"
							>
								← Back
							</button>
						{:else}
							<button
								on:click={saveRole}
								disabled={saveLoading ||
									!hasChanges ||
									(mode === 'new' && !roleData.display_name.trim())}
								class="premium-primary-btn text-sm px-4 py-2 {saveLoading ||
								!hasChanges ||
								(mode === 'new' && !roleData.display_name.trim())
									? 'opacity-50 cursor-not-allowed'
									: ''}"
							>
								{#if saveLoading}
									<div
										class="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"
									></div>
									<span>Saving...</span>
								{:else}
									<span class="text-lg">💾</span>
									<span>
										{#if mode === 'new'}
											Create Role
										{:else if mode === 'edit'}
											{#if hasChanges}
												Save Changes
											{:else}
												No Changes
											{/if}
										{/if}
									</span>
								{/if}
							</button>

							<button
								on:click={cancelEdit}
								class="premium-secondary-btn text-sm px-4 py-2"
								disabled={saveLoading}
							>
								<!-- prevent cancel during save -->
								{#if mode === 'new'}
									Cancel
								{:else if mode === 'edit'}
									{#if hasChanges}
										Discard Changes
									{:else}
										Back
									{/if}
								{:else}
									Back
								{/if}
							</button>
						{/if}
					</div>
				</div>
			</div>
		{/if}
	</div>
</div>

<style>
	/* Premium Card Styles */
	.premium-card {
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 12px;
		box-shadow:
			0 1px 3px 0 rgba(0, 0, 0, 0.1),
			0 1px 2px 0 rgba(0, 0, 0, 0.06);
		transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
	}

	.premium-card:hover {
		box-shadow:
			0 4px 6px -1px rgba(0, 0, 0, 0.1),
			0 2px 4px -1px rgba(0, 0, 0, 0.06);
		transform: translateY(-1px);
	}

	.premium-card-header {
		border-bottom: 1px solid #e5e7eb;
		padding: 1.5rem 1.5rem 0;
		margin-bottom: 1rem;
	}

	/* Input Styles */
	.premium-input {
		width: 100%;
		border: 1px solid #d1d5db;
		border-radius: 8px;
		padding: 0.75rem 1rem;
		background: white;
		transition: all 0.3s ease;
	}

	.premium-input:focus {
		outline: none;
		border-color: #4f46e5;
		box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
	}

	.premium-input:disabled {
		background: #f9fafb;
		color: #6b7280;
		cursor: not-allowed;
	}

	/* Button Styles */
	.premium-primary-btn {
		background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
		color: white;
		padding: 0.75rem 1.5rem;
		border-radius: 8px;
		font-weight: 600;
		transition: all 0.3s ease;
		box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.3);
		display: flex;
		align-items: center;
		gap: 0.5rem;
		justify-content: center;
	}

	.premium-primary-btn:hover:not(:disabled) {
		transform: translateY(-2px);
		box-shadow: 0 8px 15px -3px rgba(79, 70, 229, 0.4);
	}

	.premium-secondary-btn {
		background: white;
		color: #374151;
		border: 1px solid #d1d5db;
		padding: 0.75rem 1.5rem;
		border-radius: 8px;
		font-weight: 600;
		transition: all 0.3s ease;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		justify-content: center;
	}

	.premium-secondary-btn:hover {
		background: #f9fafb;
		border-color: #9ca3af;
	}

	/* Message Styles */
	.premium-message {
		padding: 1rem;
		border-radius: 8px;
		font-weight: 500;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.premium-message.success {
		background: #ecfdf5;
		color: #065f46;
		border: 1px solid #a7f3d0;
	}

	.premium-message.error {
		background: #fef2f2;
		color: #991b1b;
		border: 1px solid #fca5a5;
	}

	/* Responsive Design */
	@media (max-width: 1280px) {
		.grid {
			grid-template-columns: 1fr;
		}
	}

	@media (max-width: 768px) {
		.premium-card-header {
			padding: 1rem 1rem 0;
		}

		.p-6 {
			padding: 1rem;
		}

		.flex-col {
			flex-direction: column;
		}

		.flex-1 {
			flex: 1 1 100%;
		}
	}
</style>
