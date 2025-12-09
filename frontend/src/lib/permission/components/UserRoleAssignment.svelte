<script lang="ts">
  import { onMount } from 'svelte';
  import { UserUpdatePayload } from '$lib/permission/stores/types_permission';
  import { usersStore, rolesStore } from '$lib/permission/stores/permission_entity_stores';
  import { useMutations, useLookup } from '$lib/common/controls';
  import { PermissionUtils } from '$lib/permission/utils_permission';

  // Props
  export let userIds: string[] = [];
  export let mode: 'single' | 'bulk' | 'maintenance' = 'single';
  export let showHeader: boolean = true;
  export let onSave: ((roles: string[]) => void) | null = null;
  export let onCancel: (() => void) | null = null;

  // Extract inner Svelte writables exposed by the factory
  const { pagination: usersPagination } = usersStore;
  const { getEntities: getUsers } = useLookup(usersStore);

  const { pagination: rolesPagination } = rolesStore;
  const { getEntities: getRoles } = useLookup(rolesStore);


  // Internal state
  let selectedRoles = new Set<string>();
  let selectedUsers: any[] = [];
  let roleSearchQuery = '';
  let saveLoading = false;
  let saveMessage = '';
  let originalUserRoles = new Map<number, Set<string>>();
  let initialized = false;
  let expandedAdditionalFields = true;
  let roleSearchResults = []; 
  
  let userSearchQuery = '';
  let userSearchResults = [];
  
  // Additional fields (dummy for now)
  let additionalFields = {
    department: 'Sales',
    location: 'New York',
    status: 'active',
    statusEffectiveFrom: '2024-01-15'
  };

  // Mutation helpers
  const { addItem, updateItem } = useMutations(usersStore);
  const {  loading: usersLoading } = usersStore;
  // Derived data
  //$: safeUsers = $users ?? [];
  //$: safeRoles = $systemRoles ?? [];
  $: safeRoles = $rolesPagination.items ?? [];
  $: isViewMode = mode === 'single' && selectedUsers.length === 1 && !onSave;

  $: availableRoles = safeRoles.map(role => ({
    id: role.role_key,
    name: role.display_name,
    power: role.power_level || 50,
    permissions: role.permission_count || 0,
    description: role.description,
    is_system_role: role.is_system_role,
    type: role.power_level >= 60 ? 'core' : 'additional'
  }));

  $: filteredRoles = availableRoles.filter(role =>
    role.name.toLowerCase().includes(roleSearchQuery.toLowerCase()) ||
    role.description.toLowerCase().includes(roleSearchQuery.toLowerCase())
  );
  $: coreRoles = filteredRoles.filter(role => role.type === 'core');
  $: additionalRoles = filteredRoles.filter(role => role.type === 'additional');

  $: commonRoles = selectedUsers.length > 0
    ? selectedUsers.reduce((common, user, index) => {
        if (index === 0) return new Set(user.roles || []);
        return new Set([...common].filter(role => (user.roles || []).includes(role)));
      }, new Set<string>())
    : new Set<string>();

      /*
  $: {
    if (safeUsers.length > 0 && !initialized) {
      initializeSelectedUsers();
    }
  }
*/
  $: selectedRoleDetails = Array.from(selectedRoles)
    .map(roleId => availableRoles.find(role => role.id === roleId))
    .filter(Boolean);

  $: combinedPower = calculateCombinedPower();
  $: riskAssessment = getRiskAssessment();

  onMount(async () => {
    //loadUserRoles();
    await rolesStore.setView(1, 50);
    if (!initialized) {
      initializeSelectedUsers();
    }
  });

  async function initializeSelectedUsers() {
    
    if (mode === 'maintenance') {
      selectedUsers = [];
      selectedRoles = new Set();
      initialized = true;
      return;
    }
    if (userIds.length > 0) {
      console.log('initializeSelectedUsers()');
      console.log(userIds);
      //const users = safeUsers.filter(u => userIds.includes(u.user_id));
      const users = await getUsers(userIds);
      /*
      const users = await getEntities([], {
          queryFilter: { ids: userIds}
      });*/
      console.log(users);
      if (users.length > 0) {
        selectedUsers = users;
        loadUserRoles();
        initialized = true;
      }
    }
  }

  function loadUserRoles() {
    if (selectedUsers.length === 1) {
      const user = selectedUsers[0];
      if (user && user.roles) {
        selectedRoles = new Set(user.roles);
        originalUserRoles.set(user.id, new Set(user.roles));
      }
    } else if (selectedUsers.length > 1) {
      selectedRoles = new Set(Array.from(commonRoles));
      selectedUsers.forEach(user => {
        originalUserRoles.set(user.id, new Set(user.roles || []));
      });
    }
  }

  async function searchRoles() {
  if (!roleSearchQuery.trim()) {
    roleSearchResults = [];
    return;
  }
  roleSearchResults = await getRoles([], {
    queryFilter: { q: roleSearchQuery, fields: ["role_key", "description"] }
  });
}


  function toggleRole(roleId: string) {
    if (isViewMode) return;
    selectedRoles.has(roleId) ? selectedRoles.delete(roleId) : selectedRoles.add(roleId);
  }

  function calculateCombinedPower() {
    let maxPower = 0;
    selectedRoles.forEach(roleId => {
      const role = availableRoles.find(r => r.id === roleId);
      if (role && role.power > maxPower) maxPower = role.power;
    });
    return maxPower;
  }

  function getRiskAssessment() {
    const power = calculateCombinedPower();
    if (power >= 100) return { level: 'critical', message: 'User has administrative access', recommendation: 'Monitor all administrative activities', color: 'red' };
    if (power >= 80) return { level: 'high', message: 'User can manage other users', recommendation: 'Regular audit of user management activities', color: 'orange' };
    if (power >= 60) return { level: 'medium', message: 'User has content modification capabilities', recommendation: 'Standard monitoring recommended', color: 'yellow' };
    return { level: 'low', message: 'User has basic viewing access', recommendation: 'Low risk - normal operations', color: 'green' };
  }

  async function saveUserRoles() {
    if (selectedUsers.length === 0 || isViewMode) return;
    if (selectedUsers.length > 0) {
      const confirmed = confirm(`⚠️ This will REPLACE all existing roles for ${selectedUsers.length} users with the selected roles. Continue?`);
      if (!confirmed) return;
    }
    saveLoading = true;
    saveMessage = '';
    try {
      const roleArray = Array.from(selectedRoles);

      // Build parallel arrays
      const ids: (string | number)[] = selectedUsers.map(u => u.id);

      const payloads: UserUpdatePayload[] = selectedUsers.map(u => ({
        user_id: u.id,
        email: u.email,
        roles: roleArray,
        org_id:u.org_id
      }));
      
      await updateItem<UserUpdatePayload>(ids, payloads);
  
      saveMessage = `✅ Roles updated successfully for ${selectedUsers.length} user${selectedUsers.length > 1 ? 's' : ''}!`;
      selectedUsers.forEach(user => originalUserRoles.set(user.id, new Set(selectedRoles)));
      onSave?.(roleArray);
    } catch (error) {
      console.error(error);
      saveMessage = '❌ Failed to update user roles';
    } finally {
      saveLoading = false;
    }
  }

  function cancelView() {
    onCancel?.();
  }

  function cancelEdit() {
    if (selectedUsers.length === 1) {
      const originalRoles = originalUserRoles.get(selectedUsers[0].id);
      if (originalRoles) selectedRoles = new Set(originalRoles);
    } else {
      selectedRoles = new Set();
    }
    onCancel?.();
  }

  function getPowerLevelIcon(power: number) {
    return PermissionUtils.getPowerLevelIcon(power);
  }

  function getRiskColorClass(level: string) {
    const colors = {
      critical: 'bg-red-50 border-red-200 text-red-700',
      high: 'bg-orange-50 border-orange-200 text-orange-700',
      medium: 'bg-yellow-50 border-yellow-200 text-yellow-700',
      low: 'bg-green-50 border-green-200 text-green-700'
    };
    return colors[level] || colors.low;
  }

  function getHeaderTitle() {
    if (isViewMode) return 'User Role Assignment';
    switch (mode) {
      case 'single': return 'Edit User Roles';
      case 'bulk': return `Bulk Edit Roles (${selectedUsers.length} users)`;
      case 'maintenance': return 'User Role Maintenance';
      default: return 'User Role Assignment';
    }
  }

  function getActionButtonText() {
    if (isViewMode) return 'Edit Roles';
    if (selectedUsers.length === 0) return 'Apply Roles';
    return `Apply to ${selectedUsers.length} User${selectedUsers.length > 1 ? 's' : ''}`;
  }

  function toggleAdditionalFields() {
    expandedAdditionalFields = !expandedAdditionalFields;
  }

  async function searchUsers() {
    if (!userSearchQuery.trim()) {
      userSearchResults = [];
      return;
    }

    // Instead of filtering safeUsers locally:
    // userSearchResults = safeUsers.filter(...)

    // Use store lookup with filter
    userSearchResults = await getUsers([], {
      queryFilter: { q: userSearchQuery, fields: ["display_name", "email","user_id"] }
    });

    // Optionally exclude already selected
    userSearchResults = userSearchResults.filter(
      user => !selectedUsers.find(su => su.user_id === user.user_id)
    );
  }


 function addUser(user) {
    if (!selectedUsers.find(su => su.user_id === user.user_id)) {
      selectedUsers = [...selectedUsers, user];
      userSearchQuery = '';
      userSearchResults = [];
      
      // In view mode, if adding a user, switch to first user only
      if (isViewMode && selectedUsers.length > 1) {
        selectedUsers = [user];
      }
    }
  }

    function removeUser(userId) {
    selectedUsers = selectedUsers.filter(user => user.user_id !== userId);
    originalUserRoles.delete(userId);
    
    if (selectedUsers.length === 0) {
      selectedRoles = new Set();
    }
  }

    function handleEditClick() {
    // Navigate to edit mode - this would typically change the route
    if (selectedUsers.length === 1) {
      goto(`/permission/users/${selectedUsers[0].id}/edit`);
    }
  }

</script>

<div class="min-h-screen bg-gray-50 py-8">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <!-- Header -->
    {#if showHeader}
      <div class="mb-8">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-4">
            <a href="/permission/users" class="text-indigo-600 hover:text-indigo-700">
              ← Back to Users
            </a>
            <div>
              <h1 class="text-3xl font-bold text-gray-900">
                {getHeaderTitle()}
              </h1>
              {#if mode === 'single' && selectedUsers.length === 1}
                <p class="mt-2 text-lg text-gray-600">
                  {selectedUsers[0].display_name} ({selectedUsers[0].email})
                </p>
              {/if}
            </div>
          </div>
          {#if selectedUsers.length > 0}
            <div class="text-right">
              <div class="text-sm text-gray-500">Combined Power</div>
              <div class="flex items-center space-x-2">
                <span class="text-2xl">{getPowerLevelIcon(combinedPower)}</span>
                <span class="font-semibold text-gray-900">{combinedPower}/100</span>
              </div>
            </div>
          {/if}
        </div>
      </div>
    {/if}

    <!-- Loading State -->
    {#if $usersLoading}
      <div class="flex justify-center items-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        <span class="ml-4 text-gray-600">Loading data...</span>
      </div>
    {:else}
      <!-- Main Content - Side by Side Layout -->
      <div class="grid grid-cols-1 xl:grid-cols-2 gap-8">
        
        <!-- Selected Users Panel -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 class="text-xl font-semibold text-gray-900 mb-4">
            Selected Users ({selectedUsers.length})
            {#if isViewMode}
              <span class="ml-2 inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                View Only
              </span>
            {/if}
          </h2>

          <!-- User Search (disabled in view mode and single mode) -->
          {#if mode !== 'single' && !isViewMode}
            <div class="mb-4">
              <div class="relative">
                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <span class="text-gray-400">🔍</span>
                </div>
                <input
                  type="text"
                  bind:value={userSearchQuery}
                  on:input={searchUsers}
                  placeholder="Search users to add by name/email/id..."
                  class="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 w-full"
                />
              </div>

              <!-- Search Results -->
              {#if userSearchResults.length > 0}
                <div class="mt-2 border border-gray-200 rounded-lg bg-white shadow-lg max-h-60 overflow-y-auto">
                  <div class="p-2 text-sm font-medium text-gray-700 bg-gray-50">Search Results</div>
                  {#each userSearchResults as user}
                    <button 
                      type="button"
                      class="w-full text-left p-3 border-b border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors duration-150"
                      on:click={() => addUser(user)}
                      on:keydown={(e) => e.key === 'Enter' && addUser(user)}
                    >
                      <div class="font-medium text-gray-900">{user.display_name}</div>
                      <div class="text-sm text-gray-500">{user.email}</div>
                      <div class="text-xs text-gray-400 mt-1">
                        Current roles: {(user.roles || []).join(', ') || 'None'}
                      </div>
                    </button>
                  {/each}
                </div>
              {/if}
            </div>
          {/if}

          <!-- Selected Users List -->
          <div class="space-y-3 max-h-96 overflow-y-auto">
            {#if selectedUsers.length === 0}
              <div class="text-center py-8 text-gray-500">
                <div class="text-4xl mb-2">👥</div>
                {#if mode === 'maintenance' && !isViewMode}
                  <p>No users selected. Search above to add users.</p>
                {:else}
                  <p>No users selected.</p>
                {/if}
              </div>
            {:else}
              {#each selectedUsers as user}
                <div class="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors duration-200 {isViewMode ? 'bg-gray-50' : ''}">
                  <div class="flex items-start justify-between">
                    <div class="flex-1">
                      <div class="flex items-center space-x-3">
                        <div class="flex-shrink-0 h-10 w-10 bg-indigo-100 rounded-full flex items-center justify-center">
                          <span class="text-indigo-600 font-semibold text-sm">
                            {(user.display_name || 'UU').substring(0, 2).toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <div class="font-semibold text-gray-900">{user.display_name}</div>
                          <div class="text-sm text-gray-500">{user.email}</div>
                          <div class="text-xs text-gray-400 mt-1">
                            Current roles: {(user.roles || []).join(', ') || 'None'}
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <!-- Remove button (disabled in single mode and view mode) -->
                    {#if mode !== 'single' && !isViewMode}
                      <button
                        on:click={() => removeUser(user.user_id)}
                        class="text-gray-400 hover:text-red-500 transition-colors duration-200 p-1"
                        title="Remove user"
                      >
                        ❌
                      </button>
                    {/if}
                  </div>
                </div>
              {/each}

              <!-- Common Roles Indicator -->
              {#if selectedUsers.length > 1 && commonRoles.size > 0}
                <div class="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <div class="text-sm font-medium text-blue-800">Common Roles:</div>
                  <div class="text-sm text-blue-700 mt-1">
                    {Array.from(commonRoles).map(role => {
                      const roleDetail = availableRoles.find(r => r.id === role);
                      return roleDetail?.name || role;
                    }).join(', ')}
                  </div>
                </div>
              {/if}
            {/if}
          </div>
        </div>
        <!-- Available Roles Panel -->
          
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          {#if !isViewMode}
          <h2 class="text-xl font-semibold text-gray-900 mb-4">
            Available Roles           
              <span class="ml-2 text-sm font-normal text-gray-500">(View Only)</span>            
          </h2>

          <!-- Role Search (disabled in view mode) -->
          <div class="mb-4">
            <div class="relative">
              <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <span class="text-gray-400">🔍</span>
              </div>
              <input
                type="text"
                bind:value={roleSearchQuery}
                placeholder="Search roles..."
                class="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 w-full {isViewMode ? 'bg-gray-100 cursor-not-allowed' : ''}"
                disabled={isViewMode}
              />
            </div>
          </div>
          {/if}

          <!-- Core Roles Section -->
          {#if coreRoles.length > 0}
            <div class="mb-6">
              {#if isViewMode}
                <h3 class="text-lg font-medium text-gray-900 mb-3 border-b pb-2">Assigned Roles</h3>
              {:else}
                <h3 class="text-lg font-medium text-gray-900 mb-3 border-b pb-2">Core Roles</h3>
              {/if}
              <div class="space-y-2">
                {#each coreRoles as role}
                  {#if isViewMode}
                    {#if selectedRoles.has(role.id)}
                    <div class="border border-gray-200 rounded-lg p-3 transition-colors duration-200 {selectedRoles.has(role.id) ? 'border-indigo-500 bg-indigo-50' : ''} {isViewMode ? 'bg-gray-50' : 'hover:border-gray-300'}">
                      <div class="flex items-start space-x-3">
                        {#if isViewMode}
                          <!-- View mode: show indicator instead of checkbox -->
                          <div class="mt-1 h-4 w-4 flex items-center justify-center">
                            {#if selectedRoles.has(role.id)}
                              <div class="w-2 h-2 bg-indigo-600 rounded-full"></div>
                            {/if}
                          </div>
                        {:else}
                          <!-- Edit mode: show checkbox -->
                          <input
                            type="checkbox"
                            checked={selectedRoles.has(role.id)}
                            on:change={() => toggleRole(role.id)}
                            class="mt-1 h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                          />
                        {/if}
                        <div class="flex-1">
                          <div class="flex items-center justify-between">
                            <span class="font-semibold text-gray-900">{role.name}</span>
                            <div class="flex items-center space-x-2">
                              <span class="text-lg">{getPowerLevelIcon(role.power)}</span>
                              <span class="text-sm text-gray-500">Power {role.power}</span>
                            </div>
                          </div>
                          <p class="text-sm text-gray-600 mt-1">{role.description}</p>
                          <div class="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                            <span>🔐 {role.permissions} permissions</span>
                            {#if role.is_system_role}
                              <span class="bg-blue-100 text-blue-800 px-2 py-1 rounded-full">System</span>
                            {/if}
                            {#if isViewMode && selectedRoles.has(role.id)}
                              <span class="bg-green-100 text-green-800 px-2 py-1 rounded-full">Assigned</span>
                            {/if}
                          </div>
                        </div>
                      </div>
                    </div>
                    {/if}
                  {:else}
                  <div class="border border-gray-200 rounded-lg p-3 transition-colors duration-200 {selectedRoles.has(role.id) ? 'border-indigo-500 bg-indigo-50' : ''} {isViewMode ? 'bg-gray-50' : 'hover:border-gray-300'}">
                    <div class="flex items-start space-x-3">
                      {#if isViewMode}
                        <!-- View mode: show indicator instead of checkbox -->
                        <div class="mt-1 h-4 w-4 flex items-center justify-center">
                          {#if selectedRoles.has(role.id)}
                            <div class="w-2 h-2 bg-indigo-600 rounded-full"></div>
                          {/if}
                        </div>
                      {:else}
                        <!-- Edit mode: show checkbox -->
                        <input
                          type="checkbox"
                          checked={selectedRoles.has(role.id)}
                          on:change={() => toggleRole(role.id)}
                          class="mt-1 h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                        />
                      {/if}
                      <div class="flex-1">
                        <div class="flex items-center justify-between">
                          <span class="font-semibold text-gray-900">{role.name}</span>
                          <div class="flex items-center space-x-2">
                            <span class="text-lg">{getPowerLevelIcon(role.power)}</span>
                            <span class="text-sm text-gray-500">Power {role.power}</span>
                          </div>
                        </div>
                        <p class="text-sm text-gray-600 mt-1">{role.description}</p>
                        <div class="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                          <span>🔐 {role.permissions} permissions</span>
                          {#if role.is_system_role}
                            <span class="bg-blue-100 text-blue-800 px-2 py-1 rounded-full">System</span>
                          {/if}
                          {#if isViewMode && selectedRoles.has(role.id)}
                            <span class="bg-green-100 text-green-800 px-2 py-1 rounded-full">Assigned</span>
                          {/if}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/if}
                {/each}
                
              </div>
            </div>
          {/if}
          <!-- No Roles Found -->
          {#if filteredRoles.length === 0}
            <div class="text-center py-8 text-gray-500">
              <div class="text-4xl mb-2">🔍</div>
              <p>No roles found matching your search.</p>
            </div>
          {/if}
        </div>
      </div>

      <!-- Additional Fields Section -->
      <div class="mt-8 bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <button 
          type="button"
          class="w-full p-4 bg-gray-50 border-b border-gray-200 {!isViewMode ? 'cursor-pointer hover:bg-gray-100' : 'cursor-default'} transition-colors duration-200 flex items-center justify-between"
          on:click={!isViewMode ? toggleAdditionalFields : null}
          disabled={isViewMode}
          aria-expanded={expandedAdditionalFields}
        >
          <span class="font-medium text-gray-900">Additional Fields</span>
          {#if !isViewMode}
            <span class="text-gray-500 text-sm">{expandedAdditionalFields ? '▼' : '▶'}</span>
          {/if}
        </button>
        
        {#if expandedAdditionalFields}
          <div class="p-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <!-- Department Field -->
              <div>
                <label for="department" class="block text-sm font-medium text-gray-700 mb-2">Department</label>
                <input
                  id="department"
                  type="text"
                  bind:value={additionalFields.department}
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 {isViewMode ? 'bg-gray-100 cursor-not-allowed' : ''}"
                  placeholder="Enter department"
                  disabled={isViewMode}
                />
              </div>
              
              <!-- Location Field -->
              <div>
                <label for="location" class="block text-sm font-medium text-gray-700 mb-2">Location</label>
                <input
                  id="location"
                  type="text"
                  bind:value={additionalFields.location}
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 {isViewMode ? 'bg-gray-100 cursor-not-allowed' : ''}"
                  placeholder="Enter location"
                  disabled={isViewMode}
                />
              </div>
              
              <!-- Status Field -->
              <div class="md:col-span-2">
                <div class="text-sm font-medium text-gray-700 mb-2">Status</div>
                <div class="flex space-x-6">
                  <label class="flex items-center {isViewMode ? 'cursor-not-allowed' : ''}">
                    <input 
                      type="radio" 
                      value="suspend" 
                      bind:group={additionalFields.status} 
                      class="mr-2 {isViewMode ? 'cursor-not-allowed' : ''}" 
                      disabled={isViewMode} 
                    />
                    <span class={isViewMode ? 'text-gray-500' : ''}>Suspend</span>
                  </label>
                  <label class="flex items-center {isViewMode ? 'cursor-not-allowed' : ''}">
                    <input 
                      type="radio" 
                      value="active" 
                      bind:group={additionalFields.status} 
                      class="mr-2 {isViewMode ? 'cursor-not-allowed' : ''}" 
                      disabled={isViewMode} 
                    />
                    <span class={isViewMode ? 'text-gray-500' : ''}>Active</span>
                  </label>
                </div>
              </div>
              
              <!-- Status Effective Date Field -->
              <div class="md:col-span-2">
                <label for="status-effective-date" class="block text-sm font-medium text-gray-700 mb-2">Status to be effective from</label>
                <input
                  id="status-effective-date"
                  type="date"
                  bind:value={additionalFields.statusEffectiveFrom}
                  class="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 {isViewMode ? 'bg-gray-100 cursor-not-allowed' : ''}"
                  disabled={isViewMode}
                />
              </div>
            </div>
            
            <!-- Helper Text -->
            <div class="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p class="text-sm text-blue-700">
                <strong>Note:</strong> These additional fields are currently using dummy data. 
                In a real implementation, this data would be fetched from your user store and 
                saved along with role assignments.
              </p>
            </div>
          </div>
        {/if}
      </div>
      <!-- Warning Message for Multi-User -->
      {#if selectedUsers.length > 1 && !isViewMode}
        <div class="mt-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div class="flex items-start space-x-3">
            <span class="text-yellow-600 text-xl">⚠️</span>
            <div>
              <div class="font-medium text-yellow-800">Important Notice</div>
              <div class="text-yellow-700 text-sm mt-1">
                Applying roles will <strong>REPLACE</strong> all existing roles for all {selectedUsers.length} selected users. 
                This action cannot be undone.
              </div>
            </div>
          </div>
        </div>
      {/if}

      <!-- Action Buttons -->
      <div class="mt-8 flex space-x-4 justify-end">
        {#if isViewMode}
          <!-- View Mode Actions -->
          <button
            on:click={cancelView}
            class="px-6 py-3 bg-indigo-600 text-white hover:bg-indigo-700 rounded-lg font-medium transition-colors duration-200 flex items-center space-x-2"
          >
            <!--span>✏️</span-->
            <span>Cancel</span>
          </button>
          <!--a
            href="/permission/users"
            class="px-6 py-3 bg-gray-100 text-gray-700 hover:bg-gray-200 rounded-lg font-medium transition-colors duration-200 text-center"
          >
            ← Back to Users
          </a-->
        {:else}
          <!-- Edit Mode Actions -->
          <button
            on:click={cancelEdit}
            class="px-6 py-3 bg-gray-100 text-gray-700 hover:bg-gray-200 rounded-lg font-medium transition-colors duration-200"
          >
            Cancel
          </button>
          
          <button
            on:click={saveUserRoles}
            disabled={saveLoading || selectedUsers.length === 0}
            class="px-6 py-3 bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-indigo-400 rounded-lg font-medium transition-colors duration-200 flex items-center space-x-2"
          >
            {#if saveLoading}
              <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              <span>Saving...</span>
            {:else}
              <span>💾 {getActionButtonText()}</span>
            {/if}
          </button>
        {/if}
      </div>

      {#if saveMessage}
        <div class="mt-4 text-center text-sm {
          saveMessage.includes('✅') ? 'text-green-600' : 'text-red-600'
        }">
          {saveMessage}
        </div>
      {/if}
    {/if}
  </div>
</div>
